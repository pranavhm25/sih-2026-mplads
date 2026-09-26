"""Synthetic model validation — deterministic injection benchmark.

Positioning (language discipline, AGENTS_RULES.md Rule 1 + §11):

  "Controlled synthetic benchmark on the existing detection pipeline.
   Results do NOT represent production-world fraud detection accuracy."

Quantitatively evaluates the UNMODIFIED detectors (rules, compliance, NLP
duplicates, Isolation Forest, agency concentration, fusion) against a
deterministic synthetic dataset in which injected records carry explicit
ground truth.

Module layout (backend/app/services/validation/synthetic/):
    metrics.py      — pure metric math (zero-division safe), no app imports
    injection.py    — deterministic baseline generator + injectors
    benchmark.py    — scenario orchestration + evaluator + serialization
"""
