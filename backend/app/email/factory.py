from collections.abc import Callable

from app.config import Settings, get_settings
from app.email.base import EmailProvider
from app.email.smtp_provider import SMTPProvider

ProviderBuilder = Callable[[Settings], EmailProvider]


def _build_smtp_provider(settings: Settings) -> EmailProvider:
    return SMTPProvider(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        sender=settings.smtp_sender,
        use_tls=settings.smtp_use_tls,
        timeout=settings.smtp_timeout,
    )


PROVIDER_BUILDERS: dict[str, ProviderBuilder] = {
    "smtp": _build_smtp_provider,
}


def get_email_provider() -> EmailProvider:
    settings = get_settings()
    try:
        builder = PROVIDER_BUILDERS[settings.email_provider]
    except KeyError as error:
        raise ValueError(
            f"Unsupported email provider: {settings.email_provider}"
        ) from error
    return builder(settings)
