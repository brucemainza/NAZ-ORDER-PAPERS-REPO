import ast
from pathlib import Path


ROOT = Path(__file__).parents[2]
DOCUMENT = ROOT / "docs" / "ai-explanation.html"
AI_ROUTER = ROOT / "backend" / "app" / "ai" / "router.py"
CONFIG = ROOT / "backend" / "app" / "config.py"


def _ai_routes() -> set[str]:
    tree = ast.parse(AI_ROUTER.read_text())
    routes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            target = decorator.func
            if not (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "router"
                and target.attr in {"get", "post", "put", "patch", "delete"}
            ):
                continue
            path = decorator.args[0]
            if isinstance(path, ast.Constant) and isinstance(path.value, str):
                routes.add(f"/ai{path.value}")
    return routes


def _ai_environment_settings() -> set[str]:
    tree = ast.parse(CONFIG.read_text())
    settings: set[str] = set()
    prefixes = ("AI_", "OLLAMA_", "SIMILARITY_")
    exact = {
        "DUPLICATE_SIMILARITY_THRESHOLD",
        "AUTOMATIC_LINK_SIMILARITY_THRESHOLD",
        "PREVIOUSLY_ADDRESSED_THRESHOLD",
        "READINESS_AI_TIMEOUT_SECONDS",
        "WORKER_STALE_SECONDS",
    }
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getenv"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            continue
        name = node.args[0].value
        if name.startswith(prefixes) or name in exact:
            settings.add(name)
    return settings


def test_ai_documentation_covers_implemented_routes_and_settings():
    html = DOCUMENT.read_text()

    assert _ai_routes()
    assert _ai_environment_settings()
    for route in _ai_routes():
        assert route in html
    for setting in _ai_environment_settings():
        assert setting in html


def test_ai_documentation_describes_current_durable_architecture():
    html = DOCUMENT.read_text()

    for required in (
        "background_jobs",
        "outbox_events",
        "record_chunks",
        "ai_inference_runs",
        "worker_heartbeats",
        "websearch_to_tsquery",
        "FOR UPDATE SKIP LOCKED",
        "HNSW",
        "retrieval_mode",
        "ranking_score",
        "cosine_similarity",
        "20260916_0012",
    ):
        assert required in html


def test_ai_documentation_is_offline_and_removes_obsolete_implementation_claims():
    html = DOCUMENT.read_text()
    lowered = html.casefold()

    assert "mermaid source" in lowered
    assert "static diagram" in lowered
    assert '<script src="http' not in lowered
    assert "import mermaid from 'http" not in lowered
    assert "/api/embeddings" not in html
    assert "in-process bm25" not in lowered
    assert "synchronous indexing" not in lowered
    assert "similarity percentage" not in lowered


def test_ai_documentation_restores_original_diagram_style():
    html = DOCUMENT.read_text()

    assert html.count('class="legacy-diagram"') >= 2
    assert '<div class="flow"' not in html
    assert ".legacy-diagram .user" in html
    assert ".legacy-diagram .box" in html
    assert ".legacy-diagram .model" in html
    assert ".legacy-diagram .db" in html


def test_ai_documentation_ends_with_full_system_uml_component_diagram():
    html = DOCUMENT.read_text()
    uml_position = html.index('<section id="full-system-uml"')
    main_end = html.index("</main>")
    footer_position = html.index("<footer>")

    assert main_end < uml_position < footer_position
    assert html[uml_position:footer_position].count("<section") == 1
    assert 'class="uml-component-diagram"' in html
    assert "@startuml" in html
    for component in (
        "Parliamentary staff",
        "Next.js frontend",
        "FastAPI API",
        "Authentication",
        "Authorization and visibility",
        "Durable worker",
        "PostgreSQL + pgvector",
        "Ollama",
        "Document validation",
        "Alembic migrator",
        "Structured request logs",
    ):
        assert component in html
