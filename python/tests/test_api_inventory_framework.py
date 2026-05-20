import csv
import time
from pathlib import Path

import pytest


INVENTORY_CANDIDATES = [
    "api_inventory_new.csv",
    "api_inventory.csv",
    "api_inventory_backup.csv",
]


def _to_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _to_int_or_none(value):
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _normalize_methods(method_cell):
    if not method_cell:
        return []
    text = str(method_cell).strip().upper()
    if "/" in text:
        parts = [p.strip() for p in text.split("/") if p.strip()]
    else:
        parts = [text]
    return [p for p in parts if p in {"GET", "POST", "PUT", "PATCH", "DELETE"}]


def _load_inventory_rows():
    root = Path(__file__).resolve().parent.parent
    chosen = None
    for name in INVENTORY_CANDIDATES:
        candidate = root / name
        if candidate.exists():
            chosen = candidate
            break
    if not chosen:
        return []

    rows = []
    with chosen.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            route = (row.get("API Route") or "").strip()
            if not route.startswith("/"):
                continue
            methods = _normalize_methods(row.get("HTTP Method"))
            if not methods:
                continue
            rows.append(
                {
                    "route": route,
                    "methods": methods,
                    "operational": _to_bool(row.get("Operational")),
                    "status_code": _to_int_or_none(row.get("Status_Code")),
                    "category": (row.get("Category") or "").strip(),
                    "source_file": chosen.name,
                }
            )
    return rows


@pytest.fixture(scope="module")
def inventory_rows():
    rows = _load_inventory_rows()
    assert rows, "No usable rows found in api_inventory*.csv"
    return rows


@pytest.fixture
def app_route_methods(app):
    mapping = {}
    for rule in app.url_map.iter_rules():
        methods = sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})
        mapping[rule.rule] = methods
    return mapping


def test_inventory_route_method_pairs_unique(inventory_rows):
    seen = set()
    for row in inventory_rows:
        for method in row["methods"]:
            key = (row["route"], method)
            assert key not in seen, f"Duplicate route/method pair in inventory: {key}"
            seen.add(key)


def test_inventory_routes_exist_in_flask_map(inventory_rows, app_route_methods):
    missing = []
    for row in inventory_rows:
        mapped_methods = app_route_methods.get(row["route"])
        if not mapped_methods:
            missing.append(f"{row['route']} [{','.join(row['methods'])}]")
            continue
        if not any(method in mapped_methods for method in row["methods"]):
            missing.append(
                f"{row['route']} inventory={row['methods']} backend={mapped_methods}"
            )
    assert not missing, "Inventory route mismatch:\n" + "\n".join(missing[:30])


def test_inventory_operational_get_endpoints_smoke(client, inventory_rows):
    # Skip endpoints that are expensive, HTML-heavy, or intentionally complex to assert here.
    skip_prefixes = (
        "/api/project-structure",
        "/api/file-activity",
        "/api/context-index",
        "/api/history-index",
    )
    skip_exact = {
        # Environment-dependent in local test context (token tracker integrations).
        "/api/token/status",
    }

    rows = []
    for row in inventory_rows:
        if "GET" not in row["methods"]:
            continue
        if not row["operational"]:
            continue
        if "<" in row["route"] or ">" in row["route"]:
            continue
        if any(row["route"].startswith(prefix) for prefix in skip_prefixes):
            continue
        if row["route"] in skip_exact:
            continue
        rows.append(row)

    assert rows, "No operational GET endpoints selected from inventory"

    failures = []
    for row in rows:
        response = client.get(row["route"])
        expected = row["status_code"]

        # Baseline: no server crashes for operational GET routes.
        if response.status_code >= 500:
            failures.append(f"{row['route']} returned {response.status_code}")
            continue

        # If inventory captured a concrete expected status, tolerate 200/400 drift only.
        if expected is not None and response.status_code not in {expected, 200, 400}:
            failures.append(
                f"{row['route']} expected ~{expected} got {response.status_code}"
            )

    assert not failures, "Operational GET smoke failures:\n" + "\n".join(failures[:30])


def test_safe_post_endpoints_reject_invalid_payload_without_500(client):
    # Contract checks for payload-validated endpoints.
    # These calls intentionally use invalid payloads and should fail safely.
    cases = [
        ("/api/tasks/complete", {}, {400, 404}),
        ("/api/reopen-task", {}, {400, 404}),
        ("/api/seed-idea", {}, {400}),
        ("/api/query", {}, {200, 400}),
    ]

    failures = []
    for route, payload, acceptable in cases:
        resp = client.post(route, json=payload)
        if resp.status_code >= 500:
            failures.append(f"{route} returned {resp.status_code} for invalid payload")
            continue
        if resp.status_code not in acceptable:
            failures.append(
                f"{route} expected one of {sorted(acceptable)} got {resp.status_code}"
            )

    assert not failures, "Safe POST contract failures:\n" + "\n".join(failures)


@pytest.mark.parametrize("source", ["transaction", "state", "flask", "bandwidth"])
def test_terminal_feed_allowed_sources_contract(client, source):
    resp = client.get(f"/api/terminal-feed?source={source}&limit=5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["source"] == source
    assert "path" in data
    assert "lines" in data
    assert isinstance(data["lines"], list)
    assert "updatedAt" in data


def test_terminal_feed_invalid_source_rejected(client):
    resp = client.get("/api/terminal-feed?source=run_terminal&limit=5")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False
    assert "Unsupported source" in data["error"]


def test_terminal_feed_response_time_budget(client):
    start = time.perf_counter()
    resp = client.get("/api/terminal-feed?source=transaction&limit=80")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert resp.status_code == 200
    # Conservative local budget to catch obvious regressions.
    assert elapsed_ms < 1500, f"/api/terminal-feed too slow: {elapsed_ms:.1f}ms"


def test_terminal_feed_limit_bounds_enforced(client):
    # Above max should be capped server-side, not rejected.
    resp_high = client.get("/api/terminal-feed?source=transaction&limit=9999")
    assert resp_high.status_code == 200
    data_high = resp_high.get_json()
    assert data_high["success"] is True
    assert data_high["total"] <= 300

    # Non-positive values should be normalized to minimum.
    resp_low = client.get("/api/terminal-feed?source=transaction&limit=0")
    assert resp_low.status_code == 200
    data_low = resp_low.get_json()
    assert data_low["success"] is True
    assert isinstance(data_low["lines"], list)


def test_terminal_feed_line_shape_when_present(client):
    resp = client.get("/api/terminal-feed?source=state&limit=20")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    for entry in data.get("lines", []):
        assert isinstance(entry, dict)
        assert "ts" in entry
        assert "level" in entry
        assert "msg" in entry
