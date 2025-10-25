def load_context(path: str) -> str:
    """Load text content from a file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
