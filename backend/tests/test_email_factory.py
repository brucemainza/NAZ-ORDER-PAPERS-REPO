import importlib
import importlib.util

import pytest

from app.config import get_settings
from app.email.base import EmailProvider


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _load_factory_module():
    qualified_name = "app.email.factory"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        "FR-031 email provider factory has not been implemented"
    )
    return importlib.import_module(qualified_name)


def test_factory_builds_smtp_provider_from_environment(monkeypatch):
    factory = _load_factory_module()
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.parliament.gov.zm")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USERNAME", "test-mailer")
    monkeypatch.setenv("SMTP_PASSWORD", "test-secret")
    monkeypatch.setenv("SMTP_SENDER", "status@test.parliament.gov.zm")
    monkeypatch.setenv("SMTP_USE_TLS", "false")
    get_settings.cache_clear()

    provider = factory.get_email_provider()

    assert isinstance(provider, EmailProvider)
    assert provider.__class__.__name__ == "SMTPProvider"
    assert provider._host == "smtp.test.parliament.gov.zm"
    assert provider._port == 2525
    assert provider._username == "test-mailer"
    assert provider._password == "test-secret"
    assert provider._sender == "status@test.parliament.gov.zm"
    assert provider._use_tls is False


def test_factory_rejects_unknown_provider_without_falling_back(monkeypatch):
    factory = _load_factory_module()
    monkeypatch.setenv("EMAIL_PROVIDER", "unknown-vendor")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="Unsupported email provider"):
        factory.get_email_provider()
