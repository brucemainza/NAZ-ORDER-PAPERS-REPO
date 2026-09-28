# EC2 Deployment

This deployment uses Docker Compose on one EC2 host. Only the Next.js service is
published to the host. By default it listens on `127.0.0.1:3000` behind an
HTTPS reverse proxy (Nginx or an Application Load Balancer); for a plain-HTTP
deployment on the instance's public IP, set `FRONTEND_PUBLISH=80` and
`SECURE_COOKIES=false` in `.env.ec2` (browsers drop `Secure` cookies over
HTTP, so logins would not persist otherwise).

## Quick start (one command)

On a fresh Ubuntu 22.04/24.04 or Amazon Linux 2023 instance (t3.medium or
larger, 30GB root volume, security group allowing inbound TCP 22 and 80):

```bash
git clone https://github.com/brucemainza/NAZ-ORDER-PAPERS-REPO.git naz-order-papers
cd naz-order-papers
sudo bash deploy/ec2-setup.sh
```

`deploy/ec2-setup.sh` installs Docker, the Compose and Buildx plugins, Ollama
and the embedding model; adds swap on small instances; generates `.env.ec2`
with random secrets for plain HTTP on the public IP; builds and migrates;
starts the stack; creates the first Administrator (`EMP-001`, password
`naz@2026` unless `ADMIN_PASSWORD` is set, also saved to
`/root/naz-admin-credentials.txt`); and verifies the site answers on port 80.
Rerun it after `git pull` to deploy updates; it keeps the existing `.env.ec2`
and database. The manual steps below are equivalent.

Change the default `naz@2026` password after the first login — it is a
bootstrap credential, not meant for ongoing use.

The EC2 overlay gates startup on the backend's `/livez`, not `/readyz`:
`/readyz` also reports dead-lettered background jobs (for example embeddings
attempted while Ollama was down), and that must not stop the frontend from
starting. Monitor `/readyz` separately.

## Before launch

- Use an EC2 instance sized for PostgreSQL, the Next.js build, and the two Ollama
  models. GPU-backed instances may be needed for acceptable AI latency.
- Attach an EBS volume for Docker/PostgreSQL data and enable encrypted EBS
  snapshots. Do not use the instance store for `pgdata`.
- Allow inbound `80` and `443` only from the intended network. Do not allow
  `5432`, `5433`, `8000`, `8080`, or `11434` from the internet.
- Install Docker Engine and the Compose plugin, then install Ollama separately.
- Treat the seeded accounts and documented development password as bootstrap
  credentials only; change or disable them before opening the system to users.

## Provision and start

```bash
git clone <repository-url> naz-order-papers
cd naz-order-papers
cp .env.ec2.example .env.ec2
${EDITOR:-vi} .env.ec2

# The password in DATABASE_URL must be URL-encoded.
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 build backend frontend
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 up -d db backend worker frontend

# A fresh database has no user accounts. Create the first Administrator:
ADMIN_PASSWORD='choose-a-strong-password' docker compose -f docker-compose.yml \
  -f docker-compose.ec2.yml --env-file .env.ec2 run --rm -T -e ADMIN_PASSWORD \
  migrate python -m scripts.create_admin --employee-id EMP-001
```

On the EC2 host, configure Ollama to listen on an address reachable from the
Docker bridge, load the exact models named in `.env.ec2`, and keep port `11434`
firewalled from external networks. Confirm `docker compose ... ps` shows the
database, backend, worker, and frontend healthy before adding public traffic.

## Release and rollback

Use an immutable `IMAGE_TAG` for releases rather than reusing `latest`:

```bash
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 pull
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 up -d backend worker frontend
```

Run migrations before starting application traffic. Verify `/readyz` from the
backend network and the public HTTPS URL after every release. Roll back the
application image only when the migration is backward-compatible; restore the
database from backup for an incompatible schema change.

## Backups

Take encrypted, off-host PostgreSQL backups at least daily and test restoring
them to a separate instance. A minimal logical backup is:

```bash
mkdir -p /var/backups/naz-order-papers
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip > "/var/backups/naz-order-papers/$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
```

Copy backups off the instance using encrypted S3 storage with a retention
policy. Store `.env.ec2` separately in AWS Secrets Manager or an encrypted
administrative vault; never commit it.

## First smoke checks

```bash
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 ps
curl -fsS https://orders.example.gov.zm/ >/dev/null
docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
  --env-file .env.ec2 exec -T backend python -c \
  "import urllib.request; urllib.request.urlopen('http://localhost:8000/readyz')"
```