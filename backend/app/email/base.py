from abc import ABC, abstractmethod


class EmailProvider(ABC):
    """Minimal substitutable contract for transactional email delivery."""

    @abstractmethod
    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> bool:
        """Return whether the provider accepted the message for delivery."""

