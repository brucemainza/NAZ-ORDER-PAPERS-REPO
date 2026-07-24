import asyncio
import importlib
import importlib.util
import smtplib
from unittest.mock import MagicMock


def _load_email_module(module_name):
    qualified_name = f"app.email.{module_name}"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        f"FR-031 email module has not been implemented: {qualified_name}"
    )
    return importlib.import_module(qualified_name)


def test_email_provider_contract_accepts_a_substitutable_fake():
    base = _load_email_module("base")

    class FakeEmailProvider(base.EmailProvider):
        def __init__(self):
            self.messages = []

        async def send_email(
            self,
            to,
            subject,
            body,
            html_body=None,
        ):
            self.messages.append((to, subject, body, html_body))
            return True

    provider = FakeEmailProvider()

    result = asyncio.run(
        provider.send_email(
            "member@parliament.gov.zm",
            "Status changed",
            "Your question was answered.",
        )
    )

    assert result is True
    assert provider.messages == [
        (
            "member@parliament.gov.zm",
            "Status changed",
            "Your question was answered.",
            None,
        )
    ]


def test_smtp_provider_sends_message_with_mocked_connection():
    smtp_module = _load_email_module("smtp_provider")
    smtp_client = MagicMock()
    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp_client
    smtp_factory = MagicMock(return_value=smtp_context)
    provider = smtp_module.SMTPProvider(
        host="smtp.parliament.gov.zm",
        port=587,
        username="mailer",
        password="secret",
        sender="notifications@parliament.gov.zm",
        use_tls=True,
        smtp_factory=smtp_factory,
    )

    result = asyncio.run(
        provider.send_email(
            [
                "member@parliament.gov.zm",
                "clerk@parliament.gov.zm",
            ],
            "Question status changed",
            "The question is now Answered.",
            "<p>The question is now <strong>Answered</strong>.</p>",
        )
    )

    assert result is True
    smtp_factory.assert_called_once_with(
        "smtp.parliament.gov.zm",
        587,
        timeout=30.0,
    )
    smtp_client.starttls.assert_called_once()
    smtp_client.login.assert_called_once_with("mailer", "secret")
    sent_message = smtp_client.send_message.call_args.args[0]
    assert sent_message["From"] == "notifications@parliament.gov.zm"
    assert sent_message["To"] == (
        "member@parliament.gov.zm, clerk@parliament.gov.zm"
    )
    assert sent_message["Subject"] == "Question status changed"
    assert sent_message.is_multipart()


def test_smtp_provider_returns_false_without_leaking_smtp_errors():
    smtp_module = _load_email_module("smtp_provider")
    smtp_factory = MagicMock(side_effect=smtplib.SMTPException("offline"))
    provider = smtp_module.SMTPProvider(
        host="smtp.parliament.gov.zm",
        port=587,
        sender="notifications@parliament.gov.zm",
        smtp_factory=smtp_factory,
    )

    result = asyncio.run(
        provider.send_email(
            "member@parliament.gov.zm",
            "Question status changed",
            "The question is now Answered.",
        )
    )

    assert result is False
