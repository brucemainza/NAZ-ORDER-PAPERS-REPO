import re
import unicodedata


WHITESPACE_PATTERN = re.compile(r"\s+")
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9\s]")


def normalize_text(text: str) -> str:
    """Return a canonical form of text for exact-match comparison.

    Steps:
      1. Unicode NFKD decomposition.
      2. Lowercase.
      3. Remove non-alphanumeric characters except whitespace.
      4. Collapse whitespace to a single space.
      5. Strip leading/trailing whitespace.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = NON_ALPHANUMERIC_PATTERN.sub(" ", text)
    text = WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def normalize_for_embedding(text: str) -> str:
    """Return a clean string suitable for embedding generation.

    The embedding model handles its own tokenization; we just ensure
    consistent whitespace and strip surrounding noise.
    """
    if not text:
        return ""
    text = WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def build_search_text(subject: str, full_text: str) -> str:
    """Combine subject and full_text into one canonical search string."""
    return f"{subject.strip()}\n{full_text.strip()}"
