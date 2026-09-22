"""ML package — unsupervised anomaly engines.

Re-exports via module __getattr__ to avoid circular imports.
"""


def __getattr__(name: str):
    if name == "run_ml_engine":
        from app.ml.isolation_forest import run_ml_engine
        return run_ml_engine
    raise AttributeError(name)
