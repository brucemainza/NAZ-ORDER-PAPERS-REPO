# Security exceptions

## Frozen authentication dependency

Authentication was explicitly excluded from this production-hardening project.
`PyJWT==2.8.0` therefore remains unchanged and has known advisories
`PYSEC-2025-183`, `PYSEC-2026-120`, `PYSEC-2026-175`, `PYSEC-2026-177`,
`PYSEC-2026-178`, and `PYSEC-2026-179`.

The CI dependency and image scans ignore only those identifiers and still fail
for every non-authentication finding. Their output reports the ignored count, so
the exception is visible. This is a residual go-live risk, not an acceptance of
the underlying vulnerabilities. Before public or production exposure, a separate
authorized authentication project must upgrade PyJWT, regression-test token
creation/verification and session behavior, remove these exceptions, and rerun
the complete security pipeline.

Owner, formal risk acceptance, compensating controls, target remediation date,
and evidence of remediation must be recorded in the NAZ risk register. Until
then, restrict network access to approved internal users and monitor abnormal
authentication failures.
