FROM pgvector/pgvector:pg16-bookworm

USER root
RUN apt-get update \
    && apt-get install --yes --no-install-recommends age ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=0755 deploy/backup/archive-wal.sh /usr/local/bin/archive-wal.sh
COPY --chmod=0755 deploy/backup/backup.sh /usr/local/bin/backup.sh
USER postgres
