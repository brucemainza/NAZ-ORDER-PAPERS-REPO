from hashlib import sha256

from app.ai.normalization import normalize_text


def normalized_record_identity(
    item_type: str,
    subject: str,
    full_text: str,
) -> str:
    return "\x1f".join(
        (
            normalize_text(item_type),
            normalize_text(subject),
            normalize_text(full_text),
        )
    )


def record_content_hash(
    item_type: str,
    subject: str,
    full_text: str,
) -> str:
    identity = normalized_record_identity(item_type, subject, full_text)
    return sha256(identity.encode("utf-8")).hexdigest()
