# EC2 Deployment

This deployment uses Docker Compose on one EC2 host. Only the Next.js service is
published to the host, on `127.0.0.1:3000`; terminate HTTPS with Nginx or an
Application Load Balancer in front of it.

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
docker compose -f docker-compose.yml -f docker-compose.ec2 \
  --env-file .env.ec2 run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.ec2 \
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
docker compose -f docker-compose.yml -f docker-compose.ec2 \
  --env-file .env.ec2 exec -T backend python -c \
  "import urllib.request; urllib.request.urlopen('http://localhost:8000/readyz')"
```