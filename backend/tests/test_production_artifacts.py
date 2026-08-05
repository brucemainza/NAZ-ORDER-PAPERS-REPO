from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]
PRODUCTION_COMPOSE = ROOT / "deploy" / "compose.production.yml"
KUBERNETES_DIR = ROOT / "deploy" / "kubernetes"


def _yaml_documents(directory: Path) -> list[dict]:
    documents: list[dict] = []
    for path in sorted(directory.glob("*.yaml")):
        documents.extend(
            document
            for document in yaml.safe_load_all(path.read_text())
            if document
        )
    return documents


def test_production_compose_is_isolated_and_hardened():
    compose = yaml.safe_load(PRODUCTION_COMPOSE.read_text())
    services = compose["services"]

    assert {"postgres", "migrate", "api", "worker", "frontend", "ollama", "clamav"} <= set(services)
    assert "ports" not in services["postgres"]
    assert "portainer" not in services
    assert "/var/run/docker.sock" not in PRODUCTION_COMPOSE.read_text()

    for name in ("api", "worker", "frontend"):
        service = services[name]
        assert service["read_only"] is True
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["cap_drop"] == ["ALL"]
        assert service["deploy"]["resources"]["limits"]
        assert not any("./" in str(volume) for volume in service.get("volumes", []))

    assert services["api"]["deploy"]["replicas"] >= 2
    assert services["worker"]["deploy"]["replicas"] >= 2
    assert services["ollama"]["deploy"]["replicas"] >= 2
    assert services["api"]["healthcheck"]
    assert services["frontend"]["healthcheck"]


def test_production_images_run_as_unprivileged_users():
    backend = (ROOT / "deploy" / "docker" / "backend.Dockerfile").read_text()
    frontend = (ROOT / "deploy" / "docker" / "frontend.Dockerfile").read_text()

    assert "USER 10001:10001" in backend
    assert "HEALTHCHECK" in backend and "/livez" in backend
    assert "USER 10001:10001" in frontend
    assert "npm ci" in frontend
    assert "npm install" not in frontend


def test_kubernetes_workloads_have_redundancy_probes_resources_and_security():
    documents = _yaml_documents(KUBERNETES_DIR)
    workloads = {
        document["metadata"]["name"]: document
        for document in documents
        if document["kind"] in {"Deployment", "StatefulSet"}
    }

    for name in ("api", "worker", "frontend", "ollama"):
        workload = workloads[name]
        assert workload["spec"]["replicas"] >= 2
        pod_spec = workload["spec"]["template"]["spec"]
        assert pod_spec["securityContext"]["runAsNonRoot"] is True
        container = pod_spec["containers"][0]
        assert container["securityContext"]["allowPrivilegeEscalation"] is False
        assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
        assert container["resources"]["requests"]
        assert container["resources"]["limits"]

    assert workloads["api"]["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]
    assert workloads["frontend"]["spec"]["template"]["spec"]["containers"][0]["livenessProbe"]

    kinds = [document["kind"] for document in documents]
    assert kinds.count("PodDisruptionBudget") >= 3
    assert "NetworkPolicy" in kinds
    network_policies = [
        document for document in documents if document["kind"] == "NetworkPolicy"
    ]
    assert any(policy["metadata"]["name"] == "default-deny" for policy in network_policies)


def test_backup_restore_and_ci_supply_required_production_controls():
    backup = (ROOT / "deploy" / "backup" / "backup.sh").read_text()
    archive = (ROOT / "deploy" / "backup" / "archive-wal.sh").read_text()
    runbook = (ROOT / "docs" / "operations" / "backup-restore.md").read_text()
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "pg_basebackup" in backup and "age --encrypt" in backup
    assert "age --encrypt" in archive
    assert "15-minute RPO" in runbook
    assert "four-hour RTO" in runbook
    for required in (
        "pytest",
        "test:source",
        "npm run build",
        "alembic",
        "pip-audit",
        "gitleaks",
        "trivy",
        "syft",
        "cosign verify",
    ):
        assert required in workflow
