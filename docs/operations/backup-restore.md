# PostgreSQL backup and restore runbook

## Service objectives

- Target: **15-minute RPO**. PostgreSQL forces a WAL archive switch at least every
  900 seconds; alert if the newest encrypted WAL object is older than 15 minutes.
- Target: **four-hour RTO**. Rehearse a full restore every quarter and record the
  measured recovery time, integrity checks, and operator.

The production PostgreSQL image archives each WAL segment with `age` public-key
encryption. A base backup is taken every six hours and encrypted before its final
filename becomes visible. Store the age private key outside the cluster and test
decryption from the recovery environment. Replicate `/backups` and `/wal_archive`
to immutable off-site storage; a local volume is not a disaster-recovery copy.

## Backup checks

1. Confirm the latest base backup and WAL archive are present off site.
2. Confirm files are mode `0600`, encrypted, non-zero, and covered by storage
   retention/immutability policy.
3. Decrypt a sample with `age --decrypt -i /secure/key.txt` in an isolated host.
4. Alert on backup job failure, archive lag over 15 minutes, low disk space, or a
   base backup older than 12 hours.

## Point-in-time restore

1. Declare the incident, stop writers, record the requested UTC recovery time,
   and preserve the failed database volumes for forensics.
2. Provision a clean PostgreSQL 16 + pgvector instance on encrypted storage. Do
   not restore over the failed primary.
3. Fetch the last good encrypted base backup and all subsequent encrypted WAL
   objects from immutable storage. Verify storage checksums.
4. Decrypt into a restricted temporary directory, extract the base tar into the
   new PostgreSQL data directory, and set ownership to the PostgreSQL UID.
5. Configure `restore_command` to decrypt/copy the requested WAL file from the
   recovery archive and set `recovery_target_time` to the approved UTC time.
6. Start PostgreSQL, wait for consistent recovery, then promote it. Run
   `SELECT extversion FROM pg_extension WHERE extname = 'vector'`, verify the
   Alembic revision equals application head, and execute the backend smoke tests.
7. Repoint one canary API, validate record counts/search/workflow reads, then
   restore normal traffic. Restart workers only after API validation.
8. Delete decrypted temporary material securely according to the storage
   platform's procedure. Retain audit evidence and complete the incident review.

## Rollback and rehearsal

If validation fails, stop the recovery instance and repeat from the unchanged
encrypted objects at an earlier recovery target. A rehearsal is successful only
when the restored record counts, latest committed record, Alembic revision,
sample FTS/vector searches, and application readiness checks all pass within four
hours. Never test a restore against the production primary.
