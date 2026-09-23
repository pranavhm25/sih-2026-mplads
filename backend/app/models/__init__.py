"""ORM models. Importing this package registers all tables on Base.metadata."""
from app.models.models import (  # noqa: F401
    CaseEvidence,
    CaseEvent,
    CaseNote,
    Dataset,
    DetectionRun,
    InvestigationCase,
    MPAllocationRecord,
    Officer,
    PeerGroup,
    Project,
    ProjectMetrics,
    ProjectPeer,
    ProjectSignal,
    RelatedProject,
    Report,
    RuleDefinition,
    SchemeAggregate,
    SignalEvidence,
    ValidationIssue,
)

__all__ = [
    "CaseEvidence", "CaseEvent", "CaseNote", "Dataset", "DetectionRun",
    "InvestigationCase", "MPAllocationRecord", "Officer", "PeerGroup",
    "Project", "ProjectMetrics", "ProjectPeer", "ProjectSignal", "RelatedProject",
    "Report", "RuleDefinition", "SchemeAggregate", "SignalEvidence",
    "ValidationIssue",
]
