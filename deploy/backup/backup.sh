#!/bin/sh
set -eu

backup_dir="${BACKUP_DIR:-/backups}"
recipient_file="${BACKUP_AGE_RECIPIENTS_FILE:-/run/secrets/backup_age_recipients}"
retention_days="${BACKUP_RETENTION_DAYS:-35}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

case "$backup_dir" in
  /backups|/backups/*) ;;
  *) echo "BACKUP_DIR must be /backups or a child of it" >&2; exit 2 ;;
esac
test -r "$recipient_file"
mkdir -p "$backup_dir"

final_path="$backup_dir/base-$timestamp.tar.gz.age"
temporary_path="$final_path.tmp.$$"
trap 'rm -f "$temporary_path"' EXIT INT TERM

pg_basebackup \
  --checkpoint=fast \
  --format=tar \
  --gzip \
  --wal-method=stream \
  --pgdata=- \
  | age --encrypt --recipients-file "$recipient_file" --output "$temporary_path"

chmod 0600 "$temporary_path"
mv "$temporary_path" "$final_path"
trap - EXIT INT TERM
find "$backup_dir" -maxdepth 1 -type f -name 'base-*.tar.gz.age' -mtime "+$retention_days" -delete
