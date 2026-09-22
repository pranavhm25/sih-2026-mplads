"""NLP duplicate-candidate detection (PRD R6, TR-07).

Combines five independent similarity components:
  text (TF-IDF cosine) + location (haversine) + cost + category + time overlap

Output is always a *duplicate candidate* for human verification — never a
duplicate/fraud verdict (AGENTS_RULES.md Rule 1).
"""
from __future__ import annotations

import math
import re
from datetime import date

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from app.core import constants as C
from app.core.constants import Severity, SignalType, SourceType
from app.models import Project, ProjectMetrics, RelatedProject
from app.services.detection.signal_factory import add_evidence, make_signal

STOPWORDS = [
    "construction", "of", "providing", "at", "the", "and", "in", "to",
    "renovation", "upgradation", "facility", "work", "works", "building",
]

TEXT_WEIGHT = 0.40
LOCATION_WEIGHT = 0.25
COST_WEIGHT = 0.20
CATEGORY_WEIGHT = 0.10
TIME_WEIGHT = 0.05

# Pairs below this combined score are not persisted.
SCORE_THRESHOLD = C.DUPLICATE_SCORE_TRIGGER
MAX_PAIRS_PER_PROJECT = 3


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, remove generic construction stopwords."""
    t = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    t = re.sub(r"\s+", " ", t).strip()
    tokens = [w for w in t.split() if w not in STOPWORDS]
    return " ".join(tokens)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cost_similarity(a: float, b: float) -> float:
    """1 − relative difference, clamped to [0, 1]."""
    m = max(a, b)
    if m == 0:
        return 0.0
    return max(0.0, 1.0 - abs(a - b) / m)


def time_overlap(a: Project, b: Project) -> bool:
    """True when the two works' active windows plausibly overlap."""
    end_a = a.completion_date or date.max
    end_b = b.completion_date or date.max
    start_a = a.start_date or a.sanction_date
    start_b = b.start_date or b.sanction_date
    if start_a is None or start_b is None:
        return False
    return start_a <= end_b and start_b <= end_a


def location_distance(a: Project, b: Project) -> float | None:
    if a.latitude is None or a.longitude is None or b.latitude is None or b.longitude is None:
        return None
    return haversine_m(
        float(a.latitude), float(a.longitude), float(b.latitude), float(b.longitude)
    )


def combined_score(
    text_sim: float, dist_m: float | None, cost_sim: float,
    category_match: bool, overlap: bool,
) -> float:
    """Weighted fusion; missing location gracefully reweights."""
    score = text_sim * TEXT_WEIGHT + cost_sim * COST_WEIGHT
    score += (CATEGORY_WEIGHT if category_match else 0.0)
    score += (TIME_WEIGHT if overlap else 0.0)
    if dist_m is not None:
        # 1.0 within 50 m, tapering to 0 at 2 km.
        proximity = max(0.0, 1.0 - min(dist_m, 2000.0) / 2000.0)
        score += proximity * LOCATION_WEIGHT
    else:
        # Redistribute location weight proportionally to the rest.
        rest = TEXT_WEIGHT + COST_WEIGHT + CATEGORY_WEIGHT + TIME_WEIGHT
        score = score / rest * (rest + LOCATION_WEIGHT)
    return round(min(1.0, score), 4)


def detect_duplicate_candidates(
    db: Session,
    projects: list[Project],
) -> dict[str, int]:
    """Find duplicate-candidate pairs; persist RelatedProject links + signals."""
    # Clear previous candidate links for these projects.
    ids = [p.id for p in projects]
    if ids:
        db.query(RelatedProject).filter(
            (RelatedProject.project_id.in_(ids))
            | (RelatedProject.related_project_id.in_(ids))
        ).delete(synchronize_session=False)
        db.flush()

    if len(projects) < 2:
        return {}

    texts = [normalize_text(p.description or "") for p in projects]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    tfidf = vectorizer.fit_transform(texts)
    sim_matrix = cosine_similarity(tfidf)

    counters: dict[str, int] = {}
    project_by_id = {p.id: p for p in projects}

    # Iterate unique pairs.
    n = len(projects)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = projects[i], projects[j]
            text_sim = float(sim_matrix[i, j])
            if text_sim < 0.25:
                continue  # cheap prefilter before geodesic work

            dist = location_distance(a, b)
            # If both are geolocated and far apart, they are not candidates.
            if dist is not None and dist > 2000:
                continue

            cost_sim = cost_similarity(float(a.sanctioned_cost), float(b.sanctioned_cost))
            category_match = bool(a.category and a.category == b.category)
            overlap = time_overlap(a, b)

            score = combined_score(text_sim, dist, cost_sim, category_match, overlap)
            if score < SCORE_THRESHOLD:
                continue

            link = RelatedProject(
                project_id=a.id,
                related_project_id=b.id,
                text_similarity=round(text_sim, 4),
                location_distance_m=round(dist, 1) if dist is not None else None,
                cost_similarity=round(cost_sim, 4),
                category_match=category_match,
                time_overlap=overlap,
                combined_score=score,
                relation_type="DUPLICATE_CANDIDATE",
            )
            db.add(link)

            for owner, other in ((a, b), (b, a)):
                severity = (
                    Severity.HIGH if score >= C.DUPLICATE_SCORE_HIGH else Severity.MEDIUM
                )
                s = make_signal(
                    project_id=owner.id,
                    signal_type=SignalType.DUPLICATE,
                    severity=severity,
                    title=(
                        f"Potential duplicate candidate of {other.work_id} "
                        f"(similarity {score:.0%})"
                    ),
                    explanation=(
                        f"This work resembles {other.work_id} ({other.description}): "
                        f"text similarity {text_sim:.0%}"
                        + (f", {dist:.0f} m apart" if dist is not None else ", location not available")
                        + f", cost similarity {cost_sim:.0%}"
                        + (", same category" if category_match else "")
                        + ("." if overlap else ". Time windows do not overlap.")
                        + " This is a duplicate candidate for verification, not a confirmed duplicate."
                    ),
                    observed={
                        "work_id": owner.work_id,
                        "description": owner.description,
                    },
                    reference={
                        "related_work_id": other.work_id,
                        "description": other.description,
                    },
                    difference={"combined_score": score, "text_similarity": round(text_sim, 4)},
                    source_type=SourceType.NLP,
                )
                db.add(s)
                db.flush()
                db.add(add_evidence(
                    s,
                    field_name="text similarity",
                    field_value=f"{text_sim:.0%}",
                    reference_label=f"vs {other.work_id}",
                    reference_value=other.description,
                    calculation="TF-IDF cosine similarity on normalized descriptions",
                    provenance={"engine": "nlp", "method": "tfidf", "ngram": "1-2"},
                ))
                if dist is not None:
                    db.add(add_evidence(
                        s,
                        field_name="location distance",
                        field_value=f"{dist:.0f} m",
                        reference_label="vs {0}".format(other.work_id),
                        reference_value=f"({float(other.latitude):.5f}, {float(other.longitude):.5f})"
                        if other.latitude is not None else "location not available",
                        calculation="haversine great-circle distance",
                        provenance={"engine": "geo"},
                    ))
                db.add(add_evidence(
                    s,
                    field_name="cost similarity",
                    field_value=f"{cost_sim:.0%}",
                    reference_label=f"vs {other.work_id}",
                    reference_value=f"₹{float(other.sanctioned_cost):,.0f}",
                    calculation="1 − |Δcost| / max(cost)",
                    provenance={"engine": "rule"},
                ))
                counters[SignalType.DUPLICATE] = counters.get(SignalType.DUPLICATE, 0) + 1

    db.flush()

    # Persist the max duplicate score per project into metrics.
    if ids:
        links = (
            db.query(RelatedProject)
            .filter(RelatedProject.project_id.in_(ids))
            .all()
        )
        metrics = {m.project_id: m for m in db.query(ProjectMetrics).filter(
            ProjectMetrics.project_id.in_(ids))}
        for pid, m in metrics.items():
            scores = [float(l.combined_score) for l in links
                      if l.project_id == pid or l.related_project_id == pid]
            m.duplicate_score = round(max(scores), 4) if scores else None
        db.commit()

    return counters
