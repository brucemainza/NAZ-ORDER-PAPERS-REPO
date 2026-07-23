import pytest

from scripts.ingest_csv import normalize_status


@pytest.mark.parametrize(
    ("source_status", "expected"),
    [
        (None, "Archived"),
        ("", "Archived"),
        ("Historical", "Archived"),
        ("Under Review", "Under Review"),
        ("Scheduled", "Scheduled"),
    ],
)
def test_csv_statuses_are_normalized_to_supported_lifecycle_values(
    source_status,
    expected,
):
    assert normalize_status(source_status) == expected
