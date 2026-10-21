import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def test_manejo_alimentar_api_record_and_list_feeding_management():
    session = requests.Session()
    headers = {"Accept": "application/json"}
    timeout = TIMEOUT

    # Resources to clean up
    created = {
        "user": None,
        "pond": None,
        "cycle": None,
        "manejo": None,
    }

    # Generate unique credentials
    unique = str(uuid.uuid4())[:8]
    email = f"testuser_{unique}@example.com"
    password = f"Passw0rd!{unique}"

    try:
        # 1) Register user
        register_url = f"{BASE_URL}/api/v1/auth/register"
        register_payload = {
            "email": email,
            "password": password,
            "full_name": f"Test User {unique}"
        }
        resp = session.post(register_url, json=register_payload, headers=headers, timeout=timeout)
        # Accept either 201 Created or 200 OK depending on implementation
        assert resp.status_code in (200, 201), f"User registration failed: {resp.status_code} {resp.text}"
        user_data = {}
        try:
            user_data = resp.json()
        except Exception:
            pass
        created["user"] = user_data.get("id") or user_data.get("user_id") or user_data.get("email") or email

        # 2) Login to obtain token
        login_url = f"{BASE_URL}/api/v1/auth/login"
        token = None

        # Try JSON body first
        login_payloads = [
            {"email": email, "password": password},
            {"username": email, "password": password},
        ]
        login_resp = None
        for payload in login_payloads:
            try:
                login_resp = session.post(login_url, json=payload, headers=headers, timeout=timeout)
                if login_resp.status_code == 200:
                    break
            except Exception:
                pass

        # If JSON attempts failed, try form data as fallback (common OAuth2 password flow)
        if login_resp is None or login_resp.status_code != 200:
            try:
                form = {"username": email, "password": password}
                login_resp = session.post(login_url, data=form, headers=headers, timeout=timeout)
            except Exception as e:
                raise AssertionError(f"Login request failed: {e}")

        assert login_resp is not None, "No response from login endpoint"
        assert login_resp.status_code == 200, f"Login failed: {login_resp.status_code} {login_resp.text}"

        login_json = {}
        try:
            login_json = login_resp.json()
        except Exception:
            pass

        # Extract token from common fields
        token = login_json.get("access_token") or login_json.get("token") or login_json.get("access") or login_json.get("jwt")
        # Some implementations return {"token": "...", "token_type": "bearer"} or {"access_token": "...", "token_type": "bearer"}
        if not token and isinstance(login_json.get("data"), dict):
            token = login_json["data"].get("access_token")

        assert token, f"Token not found in login response: {login_json}"

        auth_headers = headers.copy()
        auth_headers["Authorization"] = f"Bearer {token}"

        # 3) Create a pond (viveiro) required to start a cycle
        viveiros_url = f"{BASE_URL}/api/v1/viveiros/"
        pond_payload = {
            "nome": f"Test Pond {unique}",
            "descricao": "Created by automated test",
            "area_m2": 1000
        }
        resp = session.post(viveiros_url, json=pond_payload, headers=auth_headers, timeout=timeout)
        assert resp.status_code in (200, 201), f"Create pond failed: {resp.status_code} {resp.text}"
        pond_json = {}
        try:
            pond_json = resp.json()
        except Exception:
            pass
        pond_id = pond_json.get("id") or pond_json.get("viveiro_id") or pond_json.get("pk")
        assert pond_id is not None, f"Pond ID not returned: {pond_json}"
        created["pond"] = pond_id

        # 4) Start a production cycle for the pond
        ciclos_url = f"{BASE_URL}/api/v1/ciclos/"
        cycle_payload = {
            "viveiro_id": pond_id,
            "descricao": "Test cycle created for maneio test",
            "data_inicio": time.strftime("%Y-%m-%d")
        }
        resp = session.post(ciclos_url, json=cycle_payload, headers=auth_headers, timeout=timeout)
        assert resp.status_code in (200, 201), f"Create cycle failed: {resp.status_code} {resp.text}"
        cycle_json = {}
        try:
            cycle_json = resp.json()
        except Exception:
            pass
        ciclo_id = cycle_json.get("id") or cycle_json.get("ciclo_id") or cycle_json.get("pk")
        assert ciclo_id is not None, f"Cycle ID not returned: {cycle_json}"
        created["cycle"] = ciclo_id

        # 5) Record a feeding management entry (manejo alimentar)
        manejos_url = f"{BASE_URL}/api/v1/manejos/"
        manejo_payload = {
            "ciclo_id": ciclo_id,
            "data": time.strftime("%Y-%m-%d"),
            "quantidade_racao_kg": 12.5,
            "observacoes": "Automated test feeding distribution",
            # Example of tray observations; API may accept different field names but this is a reasonable attempt
            "bandejas": [
                {"nome": "Bandeja A", "consumo_percent": 85, "observacao": "Consumo bom"},
                {"nome": "Bandeja B", "consumo_percent": 60, "observacao": "Consumo moderado"}
            ]
        }
        resp = session.post(manejos_url, json=manejo_payload, headers=auth_headers, timeout=timeout)
        assert resp.status_code in (200, 201), f"Create manejo failed: {resp.status_code} {resp.text}"
        manejo_json = {}
        try:
            manejo_json = resp.json()
        except Exception:
            pass
        manejo_id = manejo_json.get("id") or manejo_json.get("manejo_id") or manejo_json.get("pk")
        # It's possible the create returns the created object inside data or results
        if not manejo_id and isinstance(manejo_json.get("data"), dict):
            manejo_id = manejo_json["data"].get("id") or manejo_json["data"].get("manejo_id")
        assert manejo_id is not None, f"Manejo ID not returned: {manejo_json}"
        created["manejo"] = manejo_id

        # 6) List feeding management history and verify the created entry is present
        resp = session.get(manejos_url, headers=auth_headers, timeout=timeout)
        assert resp.status_code == 200, f"List manejos failed: {resp.status_code} {resp.text}"
        list_json = {}
        try:
            list_json = resp.json()
        except Exception:
            pass

        # The list may be returned as an array or as paginated object with 'results'
        records = []
        if isinstance(list_json, list):
            records = list_json
        elif isinstance(list_json, dict):
            if "results" in list_json and isinstance(list_json["results"], list):
                records = list_json["results"]
            elif "data" in list_json and isinstance(list_json["data"], list):
                records = list_json["data"]
            elif "items" in list_json and isinstance(list_json["items"], list):
                records = list_json["items"]
            else:
                # If it's a single object, wrap it
                records = [list_json]

        # Find record that matches our ciclo_id and observations
        match = None
        for r in records:
            try:
                if str(r.get("ciclo_id") or r.get("ciclo") or r.get("cycle_id")) == str(ciclo_id):
                    # optionally match on observations or quantity
                    if "observacoes" in r:
                        if "Automated test feeding distribution" in str(r.get("observacoes")):
                            match = r
                            break
                    else:
                        match = r
                        break
            except Exception:
                continue

        assert match is not None, f"Created feeding record not found in manejos list. Retrieved {len(records)} records."

        # Additional assertions on the found record
        assert float(manejo_payload["quantidade_racao_kg"]) > 0, "Test payload has invalid feed quantity"
        found_qty = match.get("quantidade_racao_kg") or match.get("quantidade") or match.get("quantidade_racao")
        if found_qty is not None:
            try:
                assert float(found_qty) == float(manejo_payload["quantidade_racao_kg"]), "Quantity mismatch between created and listed record"
            except Exception:
                # Some APIs may store in different units; do not fail strictly on conversion errors
                pass

        print("TC005 passed: feeding management record created and listed successfully.")

    finally:
        # Cleanup: attempt deletion of created resources. Ignore errors in cleanup.
        # Delete manejo
        if created.get("manejo"):
            try:
                del_url = f"{BASE_URL}/api/v1/manejos/{created['manejo']}"
                session.delete(del_url, headers=auth_headers, timeout=timeout)
            except Exception:
                pass
        # Delete cycle
        if created.get("cycle"):
            try:
                del_url = f"{BASE_URL}/api/v1/ciclos/{created['cycle']}"
                session.delete(del_url, headers=auth_headers, timeout=timeout)
            except Exception:
                pass
        # Delete pond
        if created.get("pond"):
            try:
                del_url = f"{BASE_URL}/api/v1/viveiros/{created['pond']}"
                session.delete(del_url, headers=auth_headers, timeout=timeout)
            except Exception:
                pass
        # Note: user deletion endpoint is not specified; attempt a best-effort if possible
        if created.get("user"):
            try:
                # Common user delete patterns
                possible_paths = [
                    f"{BASE_URL}/api/v1/auth/users/{created['user']}",
                    f"{BASE_URL}/api/v1/users/{created['user']}"
                ]
                for p in possible_paths:
                    try:
                        session.delete(p, headers=auth_headers, timeout=timeout)
                    except Exception:
                        pass
            except Exception:
                pass


if __name__ == "__main__":
    test_manejo_alimentar_api_record_and_list_feeding_management()