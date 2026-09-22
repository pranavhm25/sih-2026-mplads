"""Rules package — deterministic, explainable detection rules.

Re-exports via module __getattr__ to avoid circular imports.
"""


def __getattr__(name: str):
    if name == "run_rule_engine":
        from app.rules.engine import run_rule_engine
        return run_rule_engine
    raise AttributeError(name)
