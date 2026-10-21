import requests
import time
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def test_biometrias_api_record_and_list_biometric_samples():
    session = requests.Session()
    base = BASE_URL.rstrip('/')

    # Generate unique test user
    unique_suffix = str(int(time.time())) + "-" + uuid.uuid4().hex[:6]
    email = f"testuser+{unique_suffix}@example.com"
    password = "TestPass123!"

    headers = {"Content-Type": "application/json"}

    user_registered = False
    viveiro_id = None
    ciclo_id = None
    biometria_id = None

    try:
        # 1) Register user
        register_url = f"{base}/api/v1/auth/register"
        reg_payload = {"email": email, "password": password, "full_name": "Test User"}
        try:
            r = session.post(register_url, json=reg_payload, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise AssertionError(f"Failed to call register endpoint: {e}")

        if r.status_code not in (200, 201):
            # If registration failed, still attempt to login (user might already exist)
            # but assert that the failure is not server error
            assert r.status_code < 500, f"Register failed with server error: {r.status_code} - {r.text}"
        else:
            user_registered = True

        # 2) Login to obtain JWT
        login_url = f"{base}/api/v1/auth/login"
        # try common payload shapes
        login_payloads = [
            {"email": email, "password": password},
            {"username": email, "password": password},
            {"username": email, "password": password, "grant_type": "password"},
        ]

        token = None
        login_response = None
        for payload in login_payloads:
            try:
                r = session.post(login_url, json=payload, headers=headers, timeout=TIMEOUT)
            except requests.RequestException as e:
                raise AssertionError(f"Failed to call login endpoint: {e}")

            if r.status_code == 200:
                login_response = r
                break
            # if 401 or 422, continue trying other payload shapes
        assert login_response is not None, f"Login failed for any payload. Last response: {r.status_code} - {r.text}"

        # Extract token from common locations
        resp_json = {}
        try:
            resp_json = login_response.json()
        except ValueError:
            raise AssertionError(f"Login response is not JSON: {login_response.text}")

        token_keys = ["access_token", "token", "jwt", "accessToken"]
        for k in token_keys:
            if k in resp_json:
                token = resp_json[k]
                break
        # Some APIs return {"access_token": "...", "token_type":"bearer"}
        if not token and "data" in resp_json and isinstance(resp_json["data"], dict):
            for k in token_keys:
                if k in resp_json["data"]:
                    token = resp_json["data"][k]
                    break
        assert token, f"JWT token not found in login response: {resp_json}"

        auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 3) Create a viveiro (pond) to attach a cycle
        viveiros_url = f"{base}/api/v1/viveiros/"
        viveiro_payload = {
            "nome": f"Test Pond {unique_suffix}",
            "descricao": "Created by test",
            "area_m2": 1000
        }
        try:
            r = session.post(viveiros_url, json=viveiro_payload, headers=auth_headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise AssertionError(f"Failed to call viveiros create endpoint: {e}")

        assert r.status_code in (200, 201), f"Creating viveiro failed: {r.status_code} - {r.text}"
        try:
            viveiro_resp = r.json()
        except ValueError:
            raise AssertionError(f"viveiro create response not JSON: {r.text}")

        # try common id keys
        for k in ("id", "viveiro_id", "pk"):
            if k in viveiro_resp:
                viveiro_id = viveiro_resp[k]
                break
        if not viveiro_id and isinstance(viveiro_resp, dict):
            # sometimes returned inside data
            data = viveiro_resp.get("data") if isinstance(viveiro_resp.get("data"), dict) else viveiro_resp
            for k in ("id", "viveiro_id", "pk"):
                if k in data:
                    viveiro_id = data[k]
                    break
        assert viveiro_id, f"viveiro id not found in response: {viveiro_resp}"

        # 4) Start a production cycle for the pond
        ciclos_url = f"{base}/api/v1/ciclos/"
        ciclo_payload = {
            "viveiro_id": viveiro_id,
            "data_inicio": time.strftime("%Y-%m-%d"),
            "descricao": "Test cycle"
        }
        try:
            r = session.post(ciclos_url, json=ciclo_payload, headers=auth_headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise AssertionError(f"Failed to call ciclos create endpoint: {e}")

        assert r.status_code in (200, 201), f"Creating ciclo failed: {r.status_code} - {r.text}"
        try:
            ciclo_resp = r.json()
        except ValueError:
            raise AssertionError(f"ciclo create response not JSON: {r.text}")

        for k in ("id", "ciclo_id", "pk"):
            if k in ciclo_resp:
                ciclo_id = ciclo_resp[k]
                break
        if not ciclo_id and isinstance(ciclo_resp, dict):
            data = ciclo_resp.get("data") if isinstance(ciclo_resp.get("data"), dict) else ciclo_resp
            for k in ("id", "ciclo_id", "pk"):
                if k in data:
                    ciclo_id = data[k]
                    break
        assert ciclo_id, f"ciclo id not found in response: {ciclo_resp}"

        # 5) Record a new biometric sampling
        biometrias_url = f"{base}/api/v1/biometrias/"
        biometria_payload = {
            "ciclo_id": ciclo_id,
            "amostra": 30,
            "peso_medio_g": 2.75,
            "cv_percent": 8.5,
            "uniformidade_percent": 92,
            "condicao_saude": "boa"
        }
        try:
            r = session.post(biometrias_url, json=biometria_payload, headers=auth_headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise AssertionError(f"Failed to call biometrias create endpoint: {e}")

        assert r.status_code in (200, 201), f"Creating biometria failed: {r.status_code} - {r.text}"
        try:
            biometria_resp = r.json()
        except ValueError:
            raise AssertionError(f"biometria create response not JSON: {r.text}")

        # capture biometria id if present
        for k in ("id", "biometria_id", "pk"):
            if k in biometria_resp:
                biometria_id = biometria_resp[k]
                break
        if not biometria_id and isinstance(biometria_resp, dict):
            data = biometria_resp.get("data") if isinstance(biometria_resp.get("data"), dict) else biometria_resp
            for k in ("id", "biometria_id", "pk"):
                if k in data:
                    biometria_id = data[k]
                    break

        # Validate response contains expected values
        # Look inside top-level or data
        candidate = biometria_resp.get("data") if isinstance(biometria_resp.get("data"), dict) else biometria_resp
        assert candidate.get("ciclo_id") == ciclo_id or candidate.get("ciclo") == ciclo_id or candidate.get("cicloId") == ciclo_id, \
            f"biometria response does not reference ciclo_id: {biometria_resp}"
        # sample size and mean weight checks (tolerant to key names)
        sample_keys = ("amostra", "sample_size", "sampleCount")
        weight_keys = ("peso_medio_g", "peso_medio", "mean_weight_g", "mean_weight")
        sample_ok = any(candidate.get(k) == 30 for k in sample_keys if k in candidate)
        weight_ok = any(abs(float(candidate.get(k)) - 2.75) < 1e-6 for k in weight_keys if k in candidate and candidate.get(k) is not None)
        # If not found in response body, rely on GET to verify
        # No hard fail here; just try to ensure at least one matches or biometria_id present
        assert biometria_id or sample_ok or weight_ok, f"Created biometria not verifiable in response: {biometria_resp}"

        # 6) GET biometric history and verify the new record is present
        try:
            r = session.get(biometrias_url, headers=auth_headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise AssertionError(f"Failed to call biometrias list endpoint: {e}")
        assert r.status_code == 200, f"Listing biometrias failed: {r.status_code} - {r.text}"
        try:
            list_resp = r.json()
        except ValueError:
            raise AssertionError(f"biometrias list response not JSON: {r.text}")

        # items could be a list or inside 'items' or 'data'
        items = []
        if isinstance(list_resp, list):
            items = list_resp
        elif isinstance(list_resp, dict):
            if "items" in list_resp and isinstance(list_resp["items"], list):
                items = list_resp["items"]
            elif "data" in list_resp and isinstance(list_resp["data"], list):
                items = list_resp["data"]
            elif "results" in list_resp and isinstance(list_resp["results"], list):
                items = list_resp["results"]
            else:
                # maybe top-level dict representing single object (unlikely)
                items = [list_resp]

        # Check that at least one item matches the created biometria by ciclo_id and sample or weight
        found = False
        for it in items:
            try:
                it_ciclo = it.get("ciclo_id") or it.get("ciclo") or it.get("cicloId")
                if it_ciclo is None:
                    continue
                if str(it_ciclo) == str(ciclo_id):
                    # check sample or weight
                    it_sample = None
                    for k in sample_keys:
                        if k in it:
                            it_sample = it[k]
                            break
                    it_weight = None
                    for k in weight_keys:
                        if k in it:
                            it_weight = it[k]
                            break
                    sample_matches = (it_sample == 30)
                    weight_matches = (it_weight is not None and abs(float(it_weight) - 2.75) < 1e-6)
                    if sample_matches or weight_matches or (biometria_id and (str(it.get("id") or it.get("biometria_id") or it.get("pk")) == str(biometria_id))):
                        found = True
                        break
            except Exception:
                continue

        assert found, f"Created biometric sample not found in GET /biometrias/ response. GET returned {list_resp}"

    finally:
        # Cleanup resources if created. Attempt deletions, but ignore not-found or server errors.
        # delete ciclo
        if ciclo_id:
            try:
                del_url = f"{base}/api/v1/ciclos/{ciclo_id}"
                session.delete(del_url, headers=auth_headers, timeout=TIMEOUT)
            except Exception:
                pass
        # delete viveiro
        if viveiro_id:
            try:
                del_url = f"{base}/api/v1/viveiros/{viveiro_id}"
                session.delete(del_url, headers=auth_headers, timeout=TIMEOUT)
            except Exception:
                pass
        # Note: user deletion not guaranteed by API; skip.

    print("test_biometrias_api_record_and_list_biometric_samples: PASSED")


if __name__ == "__main__":
    test_biometrias_api_record_and_list_biometric_samples()