# Production deployment

Development remains in the root `docker-compose.yml`. Production uses
`deploy/compose.production.yml` or `deploy/kubernetes/production.yaml`; neither
publishes PostgreSQL, mounts source code, nor exposes the Docker socket.

Before deployment, replace every example image with a registry image pinned by
digest and verified by CI. Create the referenced runtime secrets out of band. The
`naz-runtime-secrets` Kubernetes Secret (or the untracked Compose environment
file) must provide `DATABASE_URL` and the existing application authentication
settings. Authentication configuration and behavior are intentionally not
defined or changed by these artifacts. The resulting authentication dependency
risk is detailed in `docs/operations/security-exceptions.md` and must be resolved
before unrestricted production exposure.

Run migrations as a one-shot release gate before scaling the API or workers. The
migration command takes a PostgreSQL advisory lock, so overlapping release jobs
fail safely. Keep API, worker, and Ollama replicas on distinct nodes where the
cluster has capacity.

The example ingress host, TLS secret, storage classes, image digests, resource
sizes, GPU scheduling, external metrics destination, SMTP relay, and secret-store
integration must be replaced for the target NAZ environment.
