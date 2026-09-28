#!/usr/bin/env bash
# Provision a fresh EC2 host and deploy the NAZ Order Papers stack.
#
#   sudo bash deploy/ec2-setup.sh
#
# Supports Ubuntu/Debian and Amazon Linux. Safe to rerun: it installs only
# what is missing, keeps the existing .env.ec2 and database, then rebuilds and
# restarts the application (use this to deploy updates after `git pull`).
#
# Optional environment overrides:
#   PUBLIC_HOST        address users type in the browser (default: public IP)
#   ADMIN_EMPLOYEE_ID  first admin login ID (default: ADMIN-001)
#   ADMIN_PASSWORD     first admin password (default: generated, printed once)
#   SKIP_OLLAMA=1      skip Ollama; AI search falls back to keyword search

set -Eeuo pipefail
trap 'echo "ERROR: command failed at line $LINENO: $BASH_COMMAND" >&2' ERR

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARNING: %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "run as root: sudo bash deploy/ec2-setup.sh"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"
[[ -f docker-compose.yml && -f docker-compose.ec2.yml ]] \
  || die "docker-compose files not found; run this from the cloned repository"

ENV_FILE=.env.ec2
EMBED_MODEL=embeddinggemma:300m
ADMIN_EMPLOYEE_ID=${ADMIN_EMPLOYEE_ID:-ADMIN-001}
CREDENTIALS_FILE=/root/naz-admin-credentials.txt
MIN_COMPOSE=2.24.4 # first release with the `!override` tag used by the EC2 file

compose() {
  docker compose -f docker-compose.yml -f docker-compose.ec2.yml \
    --env-file "$ENV_FILE" "$@"
}

# shellcheck source=/dev/null
. /etc/os-release
case "$ID" in
  ubuntu | debian) PKG=apt ;;
  amzn | rhel | centos | rocky | almalinux | fedora) PKG=rpm ;;
  *) die "unsupported OS '$ID'; use Ubuntu 22.04/24.04 or Amazon Linux 2023" ;;
esac
case "$(uname -m)" in
  x86_64) ARCH=amd64 ;;
  aarch64) ARCH=arm64 ;;
  *) die "unsupported CPU architecture $(uname -m)" ;;
esac

pkg_install() {
  if [[ $PKG == apt ]]; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q "$@"
  elif command -v dnf >/dev/null; then
    dnf install -y -q "$@"
  else
    yum install -y -q "$@"
  fi
}

# ---------------------------------------------------------------- preflight
log "Checking disk and memory"
mem_mb=$(awk '/MemTotal/ {print int($2 / 1024)}' /proc/meminfo)
need_swap=0
if ((mem_mb < 7500)) && [[ -z $(swapon --show --noheadings) ]]; then
  need_swap=1
fi
free_gb=$(df -BG --output=avail / | tail -n 1 | tr -dc '0-9')
required_gb=$((10 + need_swap * 4))
echo "RAM: ${mem_mb}MB, free disk on /: ${free_gb}GB"
((free_gb >= required_gb)) || die "only ${free_gb}GB free on /, need at least \
${required_gb}GB. In the AWS console: EC2 > Volumes > Modify the root volume to \
30GB, then run: sudo growpart /dev/nvme0n1 1 && sudo resize2fs /dev/nvme0n1p1 \
(or xfs_growfs / on Amazon Linux), and rerun this script."
((mem_mb >= 1800)) || warn "under 2GB RAM; the build will be slow. t3.medium (4GB) or larger is recommended."

if ((need_swap)); then
  log "Adding a 4GB swap file so the frontend build does not run out of memory"
  if [[ ! -f /swapfile ]]; then
    fallocate -l 4G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=4096 status=none
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
  fi
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
fi

port80=$(ss -Hltnp 'sport = :80' 2>/dev/null || true)
if [[ -n $port80 && $port80 != *docker-proxy* ]]; then
  die "port 80 is already used by another program: $port80
Stop it first (for example: sudo systemctl disable --now nginx apache2 httpd)."
fi

# ------------------------------------------------------------ base packages
log "Installing base packages"
if [[ $PKG == apt ]]; then
  apt-get update -q
  pkg_install ca-certificates curl git openssl iproute2
else
  # Amazon Linux ships curl-minimal, which already provides curl.
  command -v curl >/dev/null || pkg_install curl
  pkg_install git openssl tar gzip iproute
fi
# The Ollama installer unpacks .tar.zst archives on newer releases.
pkg_install zstd >/dev/null 2>&1 || warn "zstd is unavailable; the Ollama install may fail"

# ------------------------------------------------------------------- docker
install_cli_plugins() {
  local dir=/usr/local/lib/docker/cli-plugins tag
  mkdir -p "$dir"
  if [[ ${1:-} == compose ]] || ! docker compose version >/dev/null 2>&1; then
    curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
      -o "$dir/docker-compose"
    chmod +x "$dir/docker-compose"
  fi
  if ! docker buildx version >/dev/null 2>&1; then
    tag=$(curl -fsSLI -o /dev/null -w '%{url_effective}' https://github.com/docker/buildx/releases/latest)
    tag=${tag##*/}
    curl -fsSL "https://github.com/docker/buildx/releases/download/$tag/buildx-$tag.linux-$ARCH" \
      -o "$dir/docker-buildx"
    chmod +x "$dir/docker-buildx"
  fi
}

log "Installing Docker"
if ! command -v docker >/dev/null; then
  if [[ $PKG == apt ]]; then
    curl -fsSL https://get.docker.com | sh
  else
    pkg_install docker
  fi
fi
systemctl enable --now docker
install_cli_plugins
compose_version=$(docker compose version --short | sed 's/^v//')
if ! printf '%s\n%s\n' "$MIN_COMPOSE" "$compose_version" | sort -V -C; then
  echo "Docker Compose $compose_version is older than $MIN_COMPOSE; upgrading"
  install_cli_plugins compose
fi
docker compose version
if [[ -n ${SUDO_USER:-} && $SUDO_USER != root ]]; then
  usermod -aG docker "$SUDO_USER"
fi

# ------------------------------------------------------------------- ollama
setup_ollama() {
  if ! command -v ollama >/dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh || return 1
  fi
  # Containers reach Ollama through host.docker.internal, so it must listen
  # beyond loopback. Never open port 11434 in the EC2 security group.
  mkdir -p /etc/systemd/system/ollama.service.d
  cat >/etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
  systemctl daemon-reload
  systemctl enable ollama >/dev/null 2>&1 || true
  systemctl restart ollama || return 1
  for _ in $(seq 30); do
    curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 2
  done
  for attempt in 1 2 3; do
    ollama pull "$EMBED_MODEL" && return 0
    echo "ollama pull failed (attempt $attempt), retrying"
    sleep 5
  done
  return 1
}

if [[ ${SKIP_OLLAMA:-0} == 1 ]]; then
  warn "SKIP_OLLAMA=1: AI semantic search is disabled; keyword search still works."
else
  log "Installing Ollama and the $EMBED_MODEL embedding model"
  setup_ollama || warn "Ollama setup failed. The system still runs, but AI \
semantic search is off. Fix it later and rerun this script."
fi

# ------------------------------------------------------------ configuration
detect_public_host() {
  local token ip
  token=$(curl -fsS --connect-timeout 2 -X PUT http://169.254.169.254/latest/api/token \
    -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' 2>/dev/null || true)
  ip=$(curl -fsS --connect-timeout 2 -H "X-aws-ec2-metadata-token: $token" \
    http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
  [[ -n $ip ]] || ip=$(curl -fsS --connect-timeout 5 https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]' || true)
  echo "$ip"
}

PUBLIC_HOST=${PUBLIC_HOST:-$(detect_public_host)}
[[ -n $PUBLIC_HOST ]] || die "could not detect the public IP; rerun with PUBLIC_HOST=<ip> sudo -E bash deploy/ec2-setup.sh"

if [[ ! -f $ENV_FILE ]]; then
  log "Writing $ENV_FILE with freshly generated secrets"
  db_password=$(openssl rand -hex 24)
  cat >"$ENV_FILE" <<EOF
POSTGRES_USER=naz_user
POSTGRES_PASSWORD=$db_password
POSTGRES_DB=naz_order_papers
DATABASE_URL=postgresql+psycopg://naz_user:$db_password@db:5432/naz_order_papers
JWT_SECRET=$(openssl rand -hex 48)
FRONTEND_ORIGIN=http://$PUBLIC_HOST
# Served over plain HTTP on port 80. After adding HTTPS in front, set
# FRONTEND_PUBLISH=127.0.0.1:3000 and SECURE_COOKIES=true.
FRONTEND_PUBLISH=80
SECURE_COOKIES=false
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=$EMBED_MODEL
IMAGE_TAG=latest
EOF
  chmod 600 "$ENV_FILE"
else
  log "Keeping existing $ENV_FILE"
  if grep -q 'replace-with\|URL_ENCODED_PASSWORD' "$ENV_FILE"; then
    die "$ENV_FILE still contains placeholders from .env.ec2.example; delete it and rerun to generate one"
  fi
fi

# ------------------------------------------------------------------- deploy
log "Validating compose configuration"
compose config --quiet

log "Building images (the first build takes 5-15 minutes)"
compose build backend frontend

log "Starting the database and applying migrations"
compose up -d db
compose run --rm migrate

log "Starting backend, worker and frontend"
compose up -d --remove-orphans backend worker frontend

log "Waiting for the website to answer on port 80"
status=000
for _ in $(seq 90); do
  status=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/login || true)
  [[ $status == 200 ]] && break
  sleep 5
done
if [[ $status != 200 ]]; then
  compose ps
  compose logs --tail 60 backend frontend
  die "the site did not come up (last HTTP status: $status); see the logs above"
fi

log "Ensuring the first administrator account exists"
if [[ -z ${ADMIN_PASSWORD:-} ]]; then
  ADMIN_PASSWORD=$(openssl rand -hex 8)
fi
export ADMIN_PASSWORD
admin_result=$(compose run --rm -T -e ADMIN_PASSWORD migrate \
  python -m scripts.create_admin --employee-id "$ADMIN_EMPLOYEE_ID")
echo "$admin_result"
if [[ $admin_result == *'"created"'* ]]; then
  umask 077
  printf 'URL: http://%s\nEmployee ID: %s\nPassword: %s\n' \
    "$PUBLIC_HOST" "$ADMIN_EMPLOYEE_ID" "$ADMIN_PASSWORD" >"$CREDENTIALS_FILE"
  admin_note="Password: $ADMIN_PASSWORD   (also saved in $CREDENTIALS_FILE)"
else
  admin_note="Account already existed; its password was not changed."
fi

log "Health summary"
compose ps
compose exec -T backend python - <<'EOF' || true
import json, urllib.error, urllib.request
try:
    body = urllib.request.urlopen("http://localhost:8000/readyz", timeout=10).read()
except urllib.error.HTTPError as error:
    body = error.read()
checks = json.loads(body)["checks"]
for name, check in checks.items():
    print(f"  {name:<9} {check.get('status')}")
EOF

cat <<EOF

========================================================================
 NAZ Order Papers is running:  http://$PUBLIC_HOST

 Log in with Employee ID: $ADMIN_EMPLOYEE_ID
 $admin_note
 Change this password after the first login.

 The EC2 security group must allow inbound TCP 80 (and 22 for SSH).
 Do NOT open 5432, 8000, 8080 or 11434 to the internet.
 To deploy updates later:  git pull && sudo bash deploy/ec2-setup.sh
========================================================================
EOF
