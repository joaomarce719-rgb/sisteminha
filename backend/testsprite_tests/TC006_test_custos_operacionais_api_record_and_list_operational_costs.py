import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def test_custos_operacionais_api_record_and_list_operational_costs():
    session = requests.Session()
    created_cost_id = None

    # Register a new user
    unique = uuid.uuid4().hex[:8]
    register_payload = {
        "name": f"Test User {unique}",
        "email": f"test_user_{unique}@example.com",
        "password": "StrongP@ssw0rd!"
    }

    resp = session.post(f"{BASE_URL}/api/v1/auth/register", json=register_payload, timeout=TIMEOUT)
    assert resp.status_code in (200, 201), f"Expected 200/201 from register, got {resp.status_code}: {resp.text}"

    # Login to get token
    login_payload = {"email": register_payload["email"], "password": register_payload["password"]}
    resp = session.post(f"{BASE_URL}/api/v1/auth/login", json=login_payload, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 from login, got {resp.status_code}: {resp.text}"
    login_json = {}
    try:
        login_json = resp.json()
    except Exception:
        raise AssertionError(f"Login response is not JSON: {resp.text}")

    # Extract token (support common token key names)
    token = None
    for key in ("access_token", "token", "access", "jwt"):
        if key in login_json:
            token = login_json[key]
            break
    # Some APIs nest token under data or result
    if not token:
        for container_key in ("data", "result"):
            if container_key in login_json and isinstance(login_json[container_key], dict):
                for key in ("access_token", "token", "access", "jwt"):
                    if key in login_json[container_key]:
                        token = login_json[container_key][key]
                        break
            if token:
                break

    assert token, f"Could not extract authentication token from login response: {login_json}"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Prepare operational cost payload (using Portuguese field names per PRD)
    cost_payload = {
        "categoria": "energia",
        "valor": 150.75,
        "descricao": "Lançamento de custo operacional - teste automatizado",
        # optionally a date string; if API requires different name it may still accept this payload
        "data": time.strftime("%Y-%m-%d")
    }

    # Create operational cost entry
    resp = session.post(f"{BASE_URL}/api/v1/custos/", json=cost_payload, headers=headers, timeout=TIMEOUT)
    # Expect 201 Created on success
    assert resp.status_code == 201, f"Expected 201 from POST /api/v1/custos/, got {resp.status_code}: {resp.text}"

    created_json = {}
    try:
        created_json = resp.json()
    except Exception:
        raise AssertionError(f"POST /api/v1/custos/ response is not JSON: {resp.text}")

    # Try to extract created resource id from common patterns
    created_cost_id = None
    if isinstance(created_json, dict):
        if "id" in created_json:
            created_cost_id = created_json["id"]
        elif "data" in created_json and isinstance(created_json["data"], dict) and "id" in created_json["data"]:
            created_cost_id = created_json["data"]["id"]
        elif "result" in created_json and isinstance(created_json["result"], dict) and "id" in created_json["result"]:
            created_cost_id = created_json["result"]["id"]

    # created_cost_id may be None if API returns different shape; still proceed to GET list and validate presence by amount/description
    # Fetch list of operational costs
    resp = session.get(f"{BASE_URL}/api/v1/custos/", headers=headers, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 from GET /api/v1/custos/, got {resp.status_code}: {resp.text}"
    list_json = {}
    try:
        list_json = resp.json()
    except Exception:
        raise AssertionError(f"GET /api/v1/custos/ response is not JSON: {resp.text}")

    # Determine list of items from common structures
    items = None
    if isinstance(list_json, dict):
        for key in ("data", "items", "results", "rows"):
            if key in list_json and isinstance(list_json[key], list):
                items = list_json[key]
                break
        # If top-level is a list
        if items is None and any(isinstance(list_json.get(k), list) for k in list_json):
            # pick first list found
            for k, v in list_json.items():
                if isinstance(v, list):
                    items = v
                    break
    if items is None and isinstance(list_json, list):
        items = list_json

    assert isinstance(items, list), f"Could not find a list of operational costs in response: {list_json}"

    # Validate that the created cost is present in items either by id or by matching fields
    found = False
    for it in items:
        try:
            # support nested shapes
            if isinstance(it, dict):
                if created_cost_id and (it.get("id") == created_cost_id or (it.get("data") and it["data"].get("id") == created_cost_id)):
                    found = True
                    break
                # match by amount and description if id not available
                val = it.get("valor") or it.get("amount") or it.get("value")
                desc = it.get("descricao") or it.get("description")
                if val is not None and float(val) == float(cost_payload["valor"]) and desc and cost_payload["descricao"] in desc:
                    found = True
                    break
        except Exception:
            continue

    assert found, f"Created operational cost not found in GET /api/v1/custos/ response. Response items: {items}"

    # Optionally validate financial summaries presence in response (e.g., totals, ROA/ROE). Accept presence of keys like 'summary' or 'consolidation'
    finance_ok = False
    if isinstance(list_json, dict):
        for key in ("summary", "consolidation", "financial", "consolidacao"):
            if key in list_json:
                finance_ok = True
                break
    # Not mandatory, but warn/fail if not present? The test requires summaries, so assert presence.
    assert finance_ok, f"Expected financial summaries (e.g., 'summary' or 'consolidation') in GET /api/v1/custos/ response, got: {list_json.keys()}"

    # Cleanup: attempt to delete created cost if we have an id
    if created_cost_id:
        try:
            del_resp = session.delete(f"{BASE_URL}/api/v1/custos/{created_cost_id}", headers=headers, timeout=TIMEOUT)
            # Accept 200, 204 or 404 (already deleted/not found)
            assert del_resp.status_code in (200, 204, 404), f"Unexpected status deleting cost: {del_resp.status_code}: {del_resp.text}"
        except requests.RequestException:
            # Do not fail the test if cleanup fails due to network; just print via assertion so test flow is clear
            pass


if __name__ == "__main__":
    test_custos_operacionais_api_record_and_list_operational_costs()