"""Peer benchmarking engine (TR-08).

Builds peer groups from configurable dimensions (district + category by
default) and stores per-project benchmark context. Peer groups with fewer
than MIN_PEERS members are skipped — the system then reports "no comparable
peer group" rather than fabricating a benchmark (AGENTS_RULES.md Rule 5).
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import median

from sqlalchemy.orm import Session

from app.models import PeerGroup, Project, ProjectPeer, ProjectMetrics

MIN_PEERS = 5  # below this, a peer median is not meaningful
PEER_VERSION = "peer-v1"


def peer_key(p: Project) -> tuple[str, str]:
    """Default peer definition: district + category."""
    return (p.district, p.category or "Uncategorised")


def build_peer_groups(db: Session, dataset_id: str) -> dict[str, dict]:
    """Group projects and persist benchmark stats per project.

    Returns {project_id: benchmark-dict} for groups that met MIN_PEERS.
    """
    projects = db.query(Project).filter(Project.dataset_id == dataset_id).all()

    groups: dict[tuple[str, str], list[Project]] = defaultdict(list)
    for p in projects:
        groups[peer_key(p)].append(p)

    benchmarks: dict[str, dict] = {}
    peer_links: list[ProjectPeer] = []
    metrics_by_pid: dict[str, ProjectMetrics] = {}

    for (district, category), members in sorted(groups.items()):
        # Peer group excludes the project itself when scoring it.
        if len(members) < MIN_PEERS + 1:
            continue
        costs = sorted(float(m.sanctioned_cost) for m in members)
        group_median = median(costs)

        pg = PeerGroup(
            name=f"{district} · {category}",
            district=district,
            category=category,
            definition={
                "dimensions": ["district", "category"],
                "district": district,
                "category": category,
                "min_size": MIN_PEERS,
            },
        )
        db.add(pg)
        db.flush()

        for m in members:
            others = [c for mm, c in
                      ((x, float(x.sanctioned_cost)) for x in members) if mm.id != m.id]
            if not others:
                continue
            own = float(m.sanctioned_cost)
            peers_sorted = sorted(others)
            n = len(peers_sorted)
            # Percentile of own cost within peers (0-100).
            below = sum(1 for c in peers_sorted if c <= own)
            percentile = round(100.0 * below / n, 1)
            p75 = peers_sorted[min(n - 1, int(round(0.75 * (n - 1))))]
            p_median = median(peers_sorted)
            deviation = round((own - p_median) / p_median * 100, 1) if p_median else None

            peer_links.append(ProjectPeer(
                project_id=m.id,
                peer_group_id=pg.id,
                peer_count=n,
                median_cost=Decimal(str(round(p_median, 2))),
                p75_cost=Decimal(str(round(p75, 2))),
                percentile=Decimal(str(percentile)),
            ))
            benchmarks[m.id] = {
                "peer_group": pg.name,
                "peer_count": n,
                "median_cost": round(p_median, 2),
                "p75_cost": round(p75, 2),
                "percentile": percentile,
                "deviation_pct": deviation,
            }
            metrics_by_pid[m.id] = (m.metrics if m.metrics else ProjectMetrics(project_id=m.id))

    for link in peer_links:
        db.add(link)
    for pid, bench in benchmarks.items():
        m = metrics_by_pid[pid]
        m.cost_deviation_pct = Decimal(str(bench["deviation_pct"])) if bench["deviation_pct"] is not None else None
        m.peer_median_cost = Decimal(str(bench["median_cost"]))
        m.peer_p75_cost = Decimal(str(bench["p75_cost"]))
        m.peer_percentile = Decimal(str(bench["percentile"]))
        if m not in db:
            db.add(m)

    db.commit()
    return benchmarks
