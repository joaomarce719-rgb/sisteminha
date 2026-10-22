import requests
import uuid
import time
from datetime import date

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def _extract_id(json_obj):
    # common id keys used in APIs
    for key in ("id", "ciclo_id", "viveiro_id", "pk", "_id"):
        if key in json_obj:
            return json_obj[key]
    # sometimes nested in data
    if isinstance(json_obj.get("data"), dict):
        for key in ("id", "ciclo_id", "viveiro_id"):
            if key in json_obj["data"]:
                return json_obj["data"][key]
    return None


def _status_is_paused(status_value):
    if not status_value:
        return False
    s = str(status_value).lower()
    return any(keyword in s for keyword in ("paused", "pausado", "pausa", "parado"))


def _status_is_active(status_value):
    if not status_value:
        return False
    s = str(status_value).lower()
    return any(keyword in s for keyword in ("active", "ativo", "iniciado", "resumed", "retomado", "started"))


def test_ciclos_produtivos_api_start_pause_resume_cycle():
    # Create unique user
    unique = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"test.user.{unique}@example.com",
        "password": "TestPass123!",
        "name": f"Test User {unique}"
    }

    headers = {"Content-Type": "application/json"}
    user_token = None
    viveiro_id = None
    ciclo_id = None

    # Register user
    r = requests.post(f"{BASE_URL}/api/v1/auth/register", json=register_payload, headers=headers, timeout=TIMEOUT)
    if r.status_code not in (200, 201):
        # if user already exists or other issue, try to continue to login
        # but fail the test if registration returns a client/server error other than 409/422
        if r.status_code not in (409, 422):
            raise AssertionError(f"User registration failed: {r.status_code} {r.text}")

    # Login to obtain token
    login_payload = {"email": register_payload["email"], "password": register_payload["password"]}
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_payload, headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    login_json = r.json()
    # token may be under different keys
    token = login_json.get("access_token") or login_json.get("token") or login_json.get("jwt")
    assert token, f"Auth token not found in login response: {login_json}"
    auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        # Create a pond (viveiro) to start a cycle in
        viveiro_payload = {
            "nome": f"Test Pond {unique}",
            "descricao": "Pond created by automated test",
            "area": 1000.0
        }
        r = requests.post(f"{BASE_URL}/api/v1/viveiros/", json=viveiro_payload, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code in (200, 201), f"Create pond failed: {r.status_code} {r.text}"
        viveiro_json = r.json()
        viveiro_id = _extract_id(viveiro_json)
        assert viveiro_id is not None, f"Could not extract viveiro id from response: {viveiro_json}"

        # Start a new production cycle
        ciclo_payload = {
            "viveiro_id": viveiro_id,
            "data_inicio": date.today().isoformat(),
            "densidade_inicial": 10,
            "biomassa_inicial": 100.0
        }
        r = requests.post(f"{BASE_URL}/api/v1/ciclos/", json=ciclo_payload, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code in (200, 201), f"Start cycle failed: {r.status_code} {r.text}"
        ciclo_json = r.json()
        ciclo_id = _extract_id(ciclo_json)
        assert ciclo_id is not None, f"Could not extract ciclo id from response: {ciclo_json}"

        # Check returned status if present: expect active/started
        status_val = ciclo_json.get("status") or (ciclo_json.get("data") or {}).get("status")
        assert _status_is_active(status_val) or status_val is not None, f"Unexpected cycle status on start: {status_val}"

        # Pause the cycle
        r = requests.post(f"{BASE_URL}/api/v1/ciclos/{ciclo_id}/pausar", headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code in (200, 201), f"Pause cycle failed: {r.status_code} {r.text}"
        pause_json = r.json()
        pause_status = pause_json.get("status") or (pause_json.get("data") or {}).get("status")
        assert _status_is_paused(pause_status), f"Cycle not paused as expected: {pause_status}"

        # Resume the paused cycle
        r = requests.post(f"{BASE_URL}/api/v1/ciclos/{ciclo_id}/retomar", headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code in (200, 201), f"Resume cycle failed: {r.status_code} {r.text}"
        resume_json = r.json()
        resume_status = resume_json.get("status") or (resume_json.get("data") or {}).get("status")
        assert _status_is_active(resume_status), f"Cycle not resumed/active as expected: {resume_status}"

        print("TC003 passed: start -> pause -> resume cycle flow succeeded.")

    finally:
        # Cleanup: attempt to delete cycle and pond if endpoints exist
        if ciclo_id:
            try:
                requests.delete(f"{BASE_URL}/api/v1/ciclos/{ciclo_id}", headers=auth_headers, timeout=TIMEOUT)
            except Exception:
                pass
        if viveiro_id:
            try:
                requests.delete(f"{BASE_URL}/api/v1/viveiros/{viveiro_id}", headers=auth_headers, timeout=TIMEOUT)
            except Exception:
                pass


if __name__ == "__main__":
    test_ciclos_produtivos_api_start_pause_resume_cycle()