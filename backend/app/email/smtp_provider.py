import asyncio
import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage

from app.email.base import EmailProvider


class SMTPProvider(EmailProvider):
    """Standard SMTP implementation with provider errors contained as ``False``."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        timeout: float = 30.0,
        smtp_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._timeout = timeout
        self._smtp_factory = smtp_factory

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> bool:
        recipients = [to] if isinstance(to, str) else list(to)
        recipients = [recipient.strip() for recipient in recipients if recipient.strip()]
        if not recipients or not self._sender.strip():
            return False

        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)
        if html_body is not None:
            message.add_alternative(html_body, subtype="html")

        try:
            await asyncio.to_thread(self._send_message, message, recipients)
        except (OSError, smtplib.SMTPException):
            return False
        return True

    def _send_message(
        self,
        message: EmailMessage,
        recipients: list[str],
    ) -> None:
        with self._smtp_factory(
            self._host,
            self._port,
            timeout=self._timeout,
        ) as client:
            if self._use_tls:
                client.starttls(context=ssl.create_default_context())
            if self._username is not None and self._password is not None:
                client.login(self._username, self._password)
            client.send_message(
                message,
                from_addr=self._sender,
                to_addrs=recipients,
            )
