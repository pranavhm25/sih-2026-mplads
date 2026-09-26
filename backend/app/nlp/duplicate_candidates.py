"""NLP duplicate-candidate detection (PRD R6, TR-07).

Two-stage pipeline — "similarity ≠ duplication":

  Stage 1 (generator): TF-IDF + cosine on normalized descriptions plus the
  weighted component score (text + geo + cost + category + time). This
  measures LINGUISTIC similarity only. Government boilerplate ("Construction
  of community hall at Ward N") produces high text similarity constantly,
  so text alone is never treated as duplication evidence.

  Stage 2 (contextual validation): every surviving pair is assessed for
  independent contextual agreement — geospatial proximity (haversine on the
  existing coordinates) and implementing-agency/vendor overlap (normalized
  token overlap). The result is a transparent contextual confidence
  (high/medium/low/unavailable) that drives severity and is persisted as
  evidence.

Output is always a *duplicate candidate* for human verification — never a
duplicate/fraud verdict (AGENTS_RULES.md Rule 1). Thresholds live in
app/core/constants.py, each documented with its reason.
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

# Contextual-confidence bands over the documented weights (constants.py).
# Used in evidence provenance; the banding logic itself is explicit in
# contextual_confidence() below.
CONFIDENCE_STRONG_MIN = (
    C.DUPLICATE_CONF_WEIGHT_GEO
    + C.DUPLICATE_CONF_WEIGHT_VENDOR
    + C.DUPLICATE_CONF_WEIGHT_CONTEXT
) * 0.75


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, remove generic construction stopwords."""
    t = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    t = re.sub(r"\s+", " ", t).strip()
    tokens = [w for w in t.split() if w not in STOPWORDS]
    return " ".join(tokens)


def normalize_vendor(name: str | None) -> set[str]:
    """Core identifying tokens of an agency/vendor name.

    Deterministic: lowercase, punctuation-stripped, legal-form stopwords
    removed (DUPLICATE_VENDOR_STOPWORDS). No fuzzy matching — overlap is a
    token-set ratio.
    """
    if not name:
        return set()
    t = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    return {
        w for w in t.split()
        if w and w not in C.DUPLICATE_VENDOR_STOPWORDS and not w.isdigit()
    }


def vendor_overlap(a: str | None, b: str | None) -> tuple[bool | None, float | None]:
    """Return (same_vendor, overlap_ratio).

    (None, None) when either side lacks vendor data — the contextual signal
    is then UNAVAILABLE, never treated as a match or mismatch.
    """
    ta, tb = normalize_vendor(a), normalize_vendor(b)
    if not ta or not tb:
        return None, None
    ratio = len(ta & tb) / min(len(ta), len(tb))
    return ratio >= C.DUPLICATE_VENDOR_MIN_TOKEN_OVERLAP, round(ratio, 2)


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
    """Haversine distance, or None when either side lacks coordinates.

    Missing coordinates are NEVER treated as zero distance — they make the
    geospatial signal unavailable.
    """
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


def contextual_confidence(
    dist_m: float | None,
    same_vendor: bool | None,
    cost_sim: float,
    category_match: bool,
    overlap: bool,
) -> tuple[str, float | None, list[str]]:
    """Transparent contextual assessment for one candidate pair.

    Returns (confidence_band, confidence_score, evidence_keys). Bands:

      high        — geo-close (≤ DUPLICATE_GEO_STRONG_M) AND vendor agrees;
                    the independent signals corroborate the text match.
      medium      — one contextual signal agrees and none contradicts
                    (e.g. geo-close but vendor unknown), or the combined
                    component score itself reaches the strong band on
                    cost/category/time agreement.
      low         — contextual evidence contradicts the text match (far
                    apart, or different vendors): most plausibly generic/
                    boilerplate similarity, not duplication.
      unavailable — neither geo nor vendor data exists for the pair; the
                    text signal stands alone and is explicitly downgraded.

    Missing data degrades confidence; it is never read as agreement.
    """
    reasons: list[str] = []
    score = 0.0
    context_agrees = cost_sim >= 0.9 and (category_match or overlap)

    geo_signal: bool | None = None
    if dist_m is not None:
        geo_signal = dist_m <= C.DUPLICATE_GEO_STRONG_M
        if geo_signal:
            score += C.DUPLICATE_CONF_WEIGHT_GEO
            reasons.append("geographically proximate")
        elif dist_m > C.DUPLICATE_GEO_MAX_M:
            reasons.append("locations far apart")
        else:
            reasons.append("locations not adjacent")

    if same_vendor is not None:
        if same_vendor:
            score += C.DUPLICATE_CONF_WEIGHT_VENDOR
            reasons.append("same implementing agency")
        else:
            reasons.append("different implementing agencies")
    else:
        reasons.append("agency data unavailable")

    if context_agrees:
        score += C.DUPLICATE_CONF_WEIGHT_CONTEXT
        reasons.append("cost/category/time context agrees")

    if geo_signal is None and same_vendor is None:
        return "unavailable", None, reasons

    if geo_signal is False or same_vendor is False:
        return "low", round(score, 2), reasons

    if geo_signal and same_vendor:
        return "high", round(min(1.0, score), 2), reasons

    # Exactly one independent signal agrees (or cost/category/time context
    # corroborates with the other unknown): medium, never strong.
    return "medium", round(score, 2), reasons


def detect_duplicate_candidates(
    db: Session,
    projects: list[Project],
) -> dict[str, int]:
    """Stage-1 generate + stage-2 contextual validation (persisted)."""
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

    counters: dict[str, int] = {"high": 0, "medium": 0, "low": 0, "unavailable": 0}
    project_by_id = {p.id: p for p in projects}

    n = len(projects)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = projects[i], projects[j]
            text_sim = float(sim_matrix[i, j])
            if text_sim < 0.25:
                continue  # cheap prefilter before geodesic work

            dist = location_distance(a, b)
            # Geo gate: geolocated pairs far apart are not candidates —
            # contextual contradiction beats textual similarity.
            if dist is not None and dist > C.DUPLICATE_GEO_MAX_M:
                continue

            cost_sim = cost_similarity(float(a.sanctioned_cost), float(b.sanctioned_cost))
            category_match = bool(a.category and a.category == b.category)
            overlap = time_overlap(a, b)
            same_vendor, vendor_ratio = vendor_overlap(
                a.implementing_agency, b.implementing_agency
            )

            score = combined_score(text_sim, dist, cost_sim, category_match, overlap)
            if score < SCORE_THRESHOLD:
                continue

            confidence, conf_score, conf_reasons = contextual_confidence(
                dist, same_vendor, cost_sim, category_match, overlap
            )

            link = RelatedProject(
                project_id=a.id,
                related_project_id=b.id,
                text_similarity=round(text_sim, 4),
                location_distance_m=round(dist, 1) if dist is not None else None,
                cost_similarity=round(cost_sim, 4),
                category_match=category_match,
                time_overlap=overlap,
                vendor_match=same_vendor,
                contextual_confidence=confidence,
                combined_score=score,
                relation_type="DUPLICATE_CANDIDATE",
            )
            db.add(link)

            # Severity is contextual, not textual (Step 9): text alone is a
            # weak indicator; independent corroboration escalates it.
            if confidence == "high":
                severity = Severity.HIGH
            elif confidence == "medium":
                severity = Severity.MEDIUM
            elif confidence == "unavailable":
                severity = Severity.LOW
            else:
                severity = Severity.LOW

            vendor_text = (
                "same" if same_vendor
                else "different" if same_vendor is False
                else "unavailable"
            )
            dist_text = f"{dist:.0f} m" if dist is not None else "unavailable"

            for owner, other in ((a, b), (b, a)):
                s = make_signal(
                    project_id=owner.id,
                    signal_type=SignalType.DUPLICATE,
                    severity=severity,
                    title=(
                        f"Duplicate candidate of {other.work_id} "
                        f"(text {text_sim:.0%}, context {confidence})"
                    ),
                    explanation=(
                        f"Text similarity with {other.work_id} is {text_sim:.0%} "
                        f"({other.description}). Contextual validation: distance "
                        f"{dist_text}, vendor match {vendor_text}, cost similarity "
                        f"{cost_sim:.0%}"
                        + (", same category" if category_match else "")
                        + ("." if overlap else ". Time windows do not overlap.")
                        + f" Contextual confidence: {confidence}"
                        + (f" ({'; '.join(conf_reasons)})." if conf_reasons else ".")
                        + (" High textual similarity but insufficient contextual "
                           "evidence — treat as boilerplate similarity until "
                           "verified." if confidence in ("low", "unavailable") else
                           " This is a duplicate candidate for verification, "
                           "not a confirmed duplicate.")
                    ),
                    observed={
                        "work_id": owner.work_id,
                        "description": owner.description,
                    },
                    reference={
                        "related_work_id": other.work_id,
                        "description": other.description,
                    },
                    difference={
                        "combined_score": score,
                        "text_similarity": round(text_sim, 4),
                        "contextual_confidence": confidence,
                        "contextual_score": conf_score,
                        "vendor_match": vendor_text,
                    },
                    source_type=SourceType.NLP,
                )
                db.add(s)
                db.flush()
                db.add(add_evidence(
                    s,
                    field_name="text similarity (generator)",
                    field_value=f"{text_sim:.0%}",
                    reference_label=f"vs {other.work_id}",
                    reference_value=other.description,
                    calculation="TF-IDF cosine similarity on normalized descriptions",
                    provenance={"engine": "nlp", "method": "tfidf", "ngram": "1-2"},
                ))
                db.add(add_evidence(
                    s,
                    field_name="geospatial proximity",
                    field_value=dist_text,
                    reference_label=f"strong band ≤ {C.DUPLICATE_GEO_STRONG_M:.0f} m",
                    reference_value=(
                        f"({float(other.latitude):.5f}, {float(other.longitude):.5f})"
                        if other.latitude is not None else "location not available"
                    ),
                    calculation="haversine great-circle distance",
                    provenance={"engine": "geo", "signal": "contextual"},
                ))
                db.add(add_evidence(
                    s,
                    field_name="vendor overlap",
                    field_value=vendor_text,
                    reference_label="implementing agency",
                    reference_value=(other.implementing_agency or "unavailable"),
                    calculation=(
                        f"normalized token overlap {vendor_ratio:.0%}"
                        if vendor_ratio is not None
                        else "agency data unavailable for one/both works"
                    ),
                    provenance={"engine": "vendor", "signal": "contextual"},
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
                db.add(add_evidence(
                    s,
                    field_name="contextual confidence",
                    field_value=confidence,
                    reference_label="band definition",
                    reference_value=(
                        "high = geo-close + same agency; low/unavailable = "
                        "text-only or contradictory context"
                    ),
                    calculation=(
                        f"weights: geo {C.DUPLICATE_CONF_WEIGHT_GEO}, "
                        f"vendor {C.DUPLICATE_CONF_WEIGHT_VENDOR}, "
                        f"context {C.DUPLICATE_CONF_WEIGHT_CONTEXT}"
                    ),
                    provenance={
                        "engine": "contextual",
                        "reasons": conf_reasons,
                    },
                ))
                counters[confidence] = counters.get(confidence, 0) + 1

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
