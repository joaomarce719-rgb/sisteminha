import requests
import uuid
import time
import sys

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def _extract_token(login_json):
    # Common token fields used by JWT APIs
    for key in ("access_token", "token", "jwt", "accessToken"):
        if key in login_json:
            return login_json[key]
    # Sometimes wrapped in data or result
    for wrapper in ("data", "result", "payload"):
        if wrapper in login_json and isinstance(login_json[wrapper], dict):
            for key in ("access_token", "token", "jwt", "accessToken"):
                if key in login_json[wrapper]:
                    return login_json[wrapper][key]
    raise AssertionError(f"Authentication token not found in login response: {login_json}")


def _get_list_from_response(resp_json):
    # Normalize paginated or plain list responses
    if isinstance(resp_json, list):
        return resp_json
    for key in ("results", "items", "data", "simulations", "rows"):
        if key in resp_json and isinstance(resp_json[key], list):
            return resp_json[key]
    # If it's a dict representing a single simulation, return list with it
    if isinstance(resp_json, dict):
        return [resp_json]
    raise AssertionError(f"Unexpected simulations list format: {resp_json}")


def test_simulacao_despesca_api_execute_and_list_simulations():
    session = requests.Session()

    # 1) Register a new user
    unique = uuid.uuid4().hex[:8]
    email = f"testrunner_{unique}@example.com"
    password = "TestPass123!"
    register_url = f"{BASE_URL}/api/v1/auth/register"
    register_payload = {
        "email": email,
        "password": password,
        "nome": "Test Runner"
    }

    try:
        r = session.post(register_url, json=register_payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise SystemExit(f"Failed to connect to register endpoint: {e}")

    assert r.status_code in (200, 201), f"User registration failed: {r.status_code} {r.text}"

    # 2) Login to obtain JWT token
    login_url = f"{BASE_URL}/api/v1/auth/login"
    login_payload = {"email": email, "password": password}
    try:
        r = session.post(login_url, json=login_payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise SystemExit(f"Failed to connect to login endpoint: {e}")

    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    login_json = r.json()
    token = _extract_token(login_json)
    assert isinstance(token, str) and len(token) > 0, "Empty token returned from login"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 3) Execute simulation (POST /api/v1/simulacao/)
    simulacao_url = f"{BASE_URL}/api/v1/simulacao/"
    # Construct a plausible simulation payload based on PRD (cycle data + scenario inputs)
    simulacao_payload = {
        # Many implementations accept either a ciclo_id or cycle metadata; include both common fields
        "ciclo_id": None,
        "biomassa_atual": 150.0,
        "peso_medio": 10.5,
        "sobrevivencia": 0.95,
        "cenario": {
            "preco_kg": 28.5,
            "custo_diario": 180.0,
            "taxa_mortalidade": 0.02,
            "dias_ate_colheita": 15
        },
        "descricao": f"Teste automatizado {unique}"
    }

    sim_id = None
    try:
        try:
            r = session.post(simulacao_url, json=simulacao_payload, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise SystemExit(f"Failed to connect to simulacao POST endpoint: {e}")

        # Expect a successful execution with a recommendation (per PRD -> 200)
        assert r.status_code == 200, f"Simulacao POST returned unexpected status {r.status_code}: {r.text}"
        sim_response = r.json()
        assert isinstance(sim_response, dict), f"Expected JSON object from simulacao POST, got: {sim_response}"

        # Validate presence of expected recommendation fields
        possible_keys = ("delta_v", "deltaV", "recomendacao", "recommendation", "decision", "resultado")
        if not any(k in sim_response for k in possible_keys):
            raise AssertionError(f"Simulacao response missing expected recommendation keys. Response: {sim_response}")

        # Try to extract an ID for cleanup and verification
        for id_key in ("id", "simulacao_id", "simulation_id", "_id"):
            if id_key in sim_response:
                sim_id = sim_response[id_key]
                break

        # 4) List historical simulations (GET /api/v1/simulacao/)
        try:
            r_list = session.get(simulacao_url, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise SystemExit(f"Failed to connect to simulacao GET endpoint: {e}")

        assert r_list.status_code == 200, f"Simulacao GET returned unexpected status {r_list.status_code}: {r_list.text}"
        list_json = r_list.json()
        sims = _get_list_from_response(list_json)

        # Validate that the list includes the recently created simulation if we have its id,
        # otherwise ensure there is at least one historical simulation returned.
        if sim_id is not None:
            found = any(((isinstance(item, dict) and any(item.get(k) == sim_id for k in ("id", "simulacao_id", "simulation_id", "_id"))) for item in sims))
            assert found, f"Created simulation with id {sim_id} not found in simulations list: {sims}"
        else:
            assert len(sims) > 0, f"No simulations returned in list: {list_json}"

    finally:
        # Cleanup: attempt to delete the simulation if we have an ID.
        if sim_id is not None:
            delete_url = f"{BASE_URL}/api/v1/simulacao/{sim_id}"
            try:
                r_del = session.delete(delete_url, headers=headers, timeout=TIMEOUT)
                # Accept 200, 204, 202 as successful deletes; if 404/405, it's okay (no delete endpoint or already removed)
                if r_del.status_code not in (200, 202, 204, 404, 405):
                    # Not raising to avoid masking test results, but assert to surface unexpected responses
                    assert False, f"Unexpected response when deleting simulation {sim_id}: {r_del.status_code} {r_del.text}"
            except requests.RequestException:
                # If delete fails due to connectivity, propagate nothing new; test primary assertions already handled
                pass


if __name__ == "__main__":
    try:
        test_simulacao_despesca_api_execute_and_list_simulations()
        print("TC007: PASS")
    except AssertionError as e:
        print("TC007: FAIL", e)
        sys.exit(1)
    except Exception as ex:
        print("TC007: ERROR", ex)
        sys.exit(2)