#!/bin/sh
set -eu

wal_name="${1:?WAL file name is required}"
wal_path="${2:?WAL source path is required}"
recipient_file="${BACKUP_AGE_RECIPIENTS_FILE:-/run/secrets/backup_age_recipients}"
archive_dir="${WAL_ARCHIVE_DIR:-/wal_archive}"

case "$wal_name" in
  *[!A-F0-9.]*) echo "Refusing invalid WAL name" >&2; exit 2 ;;
esac
test -r "$recipient_file"
test -r "$wal_path"
mkdir -p "$archive_dir"

final_path="$archive_dir/$wal_name.age"
temporary_path="$final_path.tmp.$$"
trap 'rm -f "$temporary_path"' EXIT INT TERM

if test -f "$final_path"; then
  exit 0
fi

age --encrypt --recipients-file "$recipient_file" --output "$temporary_path" "$wal_path"
chmod 0600 "$temporary_path"
mv "$temporary_path" "$final_path"
trap - EXIT INT TERM
