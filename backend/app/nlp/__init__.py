"""NLP package — duplicate-candidate engines.

Re-exports via module __getattr__ to avoid circular imports.
"""


def __getattr__(name: str):
    if name == "detect_duplicate_candidates":
        from app.nlp.duplicate_candidates import detect_duplicate_candidates
        return detect_duplicate_candidates
    raise AttributeError(name)
