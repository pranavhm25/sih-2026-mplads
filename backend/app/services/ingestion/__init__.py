"""Ingestion package — official import pipeline (Prompt 3).

Public entrypoint: `import_official_file` (orchestrator.py).
Supporting modules: normalizers, registry (source field registry), parsers,
validation.
"""
from app.services.ingestion.orchestrator import import_official_file  # noqa: F401
