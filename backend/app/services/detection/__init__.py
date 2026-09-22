"""Detection orchestration package.

Engines live in their ARCHITECTURE.md packages (app/rules, app/ml,
app/nlp); these re-exports keep existing imports working.
"""


def __getattr__(name: str):
    if name == "run_ml_engine":
        from app.ml.isolation_forest import run_ml_engine
        return run_ml_engine
    if name == "detect_duplicate_candidates":
        from app.nlp.duplicate_candidates import detect_duplicate_candidates
        return detect_duplicate_candidates
    if name == "run_rule_engine":
        from app.rules.engine import run_rule_engine
        return run_rule_engine
    raise AttributeError(name)
