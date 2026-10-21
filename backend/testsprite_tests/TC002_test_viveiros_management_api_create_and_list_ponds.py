import requests
import uuid
import sys
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def register_user(email, password, name):
    url = f"{BASE_URL}/api/v1/auth/register"
    payload = {
        "email": email,
        "password": password,
        "nome": name
    }
    resp = requests.post(url, json=payload, timeout=TIMEOUT)
    return resp


def login_user(email, password):
    url = f"{BASE_URL}/api/v1/auth/login"
    payload = {"email": email, "password": password}
    resp = requests.post(url, json=payload, timeout=TIMEOUT)
    return resp


def create_pond(token, pond_payload):
    url = f"{BASE_URL}/api/v1/viveiros/"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(url, json=pond_payload, headers=headers, timeout=TIMEOUT)
    return resp


def list_ponds(token, params=None):
    url = f"{BASE_URL}/api/v1/viveiros/"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params=params or {}, timeout=TIMEOUT)
    return resp


def delete_pond(token, viveiro_id):
    url = f"{BASE_URL}/api/v1/viveiros/{viveiro_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.delete(url, headers=headers, timeout=TIMEOUT)
    return resp


def extract_token_from_login_response(resp):
    j = {}
    try:
        j = resp.json()
    except Exception:
        return None
    # Common patterns
    if "access_token" in j:
        return j["access_token"]
    if "token" in j:
        return j["token"]
    if "data" in j and isinstance(j["data"], dict) and "access_token" in j["data"]:
        return j["data"]["access_token"]
    return None


def find_list_in_response(json_body):
    # Possible keys for list: items, results, data, results
    candidates = []
    if isinstance(json_body, dict):
        for key in ("items", "results", "data", "vivieros", "results"):
            if key in json_body and isinstance(json_body[key], list):
                candidates.append(json_body[key])
        # Some APIs embed list under "data"."items"
        if "data" in json_body and isinstance(json_body["data"], dict):
            for key in ("items", "results", "vivieros"):
                if key in json_body["data"] and isinstance(json_body["data"][key], list):
                    candidates.append(json_body["data"][key])
    elif isinstance(json_body, list):
        candidates.append(json_body)
    return candidates[0] if candidates else None


def test_viveiros_management_api_create_and_list_ponds():
    # Prepare unique user credentials
    unique = str(uuid.uuid4())[:8]
    email = f"testuser+{unique}@example.com"
    password = "TestPass123!"
    name = f"Test User {unique}"

    token = None
    created_viveiro_id = None

    # 1) Register user (ignore if already exists)
    try:
        resp = register_user(email, password, name)
    except Exception as e:
        raise AssertionError(f"Registration request failed: {e}")

    if resp.status_code not in (200, 201, 409):
        # if unexpected status, fail early
        raise AssertionError(f"Unexpected register status {resp.status_code}: {resp.text}")

    # If 409 (conflict), assume user exists and proceed to login

    # 2) Login to get token
    try:
        resp = login_user(email, password)
    except Exception as e:
        raise AssertionError(f"Login request failed: {e}")

    if resp.status_code != 200:
        raise AssertionError(f"Login failed with status {resp.status_code}: {resp.text}")

    token = extract_token_from_login_response(resp)
    if not token:
        raise AssertionError(f"Login response did not contain a token: {resp.text}")

    # 3) Create a new pond
    pond_payload = {
        "nome": f"Automated Test Pond {unique}",
        "descricao": "Created by automated test_viveiros_management_api_create_and_list_ponds",
        "area_m2": 1200,
        "capacidade": 5000,
        "codigo": f"TP-{unique}"
    }

    try:
        resp = create_pond(token, pond_payload)
    except Exception as e:
        raise AssertionError(f"Create pond request failed: {e}")

    if resp.status_code not in (200, 201):
        raise AssertionError(f"Create pond failed with status {resp.status_code}: {resp.text}")

    try:
        created = resp.json()
    except Exception:
        raise AssertionError(f"Create pond response is not valid JSON: {resp.text}")

    # Attempt to extract created id from common places
    created_viveiro_id = None
    if isinstance(created, dict):
        for key in ("id", "viveiro_id", "viveiro", "data"):
            if key in created:
                val = created[key]
                if isinstance(val, dict) and "id" in val:
                    created_viveiro_id = val["id"]
                    break
                if isinstance(val, (str, int)):
                    created_viveiro_id = val
                    break
        # Direct id at root
        if "id" in created and created_viveiro_id is None:
            created_viveiro_id = created["id"]

    if not created_viveiro_id:
        # Try to find numeric/string id anywhere
        def search_for_id(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "id" and isinstance(v, (str, int)):
                        return v
                    res = search_for_id(v)
                    if res:
                        return res
            elif isinstance(obj, list):
                for item in obj:
                    res = search_for_id(item)
                    if res:
                        return res
            return None

        created_viveiro_id = search_for_id(created)

    assert created_viveiro_id, f"Could not determine created viveiro id from response: {created}"

    # 4) List ponds and verify our pond is present and KPIs exist
    try:
        resp = list_ponds(token)
    except Exception as e:
        # Clean up then fail
        try:
            if created_viveiro_id:
                delete_pond(token, created_viveiro_id)
        except Exception:
            pass
        raise AssertionError(f"List ponds request failed: {e}")

    if resp.status_code != 200:
        # Clean up then fail
        try:
            delete_pond(token, created_viveiro_id)
        except Exception:
            pass
        raise AssertionError(f"List ponds failed with status {resp.status_code}: {resp.text}")

    try:
        listing = resp.json()
    except Exception:
        try:
            delete_pond(token, created_viveiro_id)
        except Exception:
            pass
        raise AssertionError(f"List ponds response is not valid JSON: {resp.text}")

    # Extract list of ponds
    ponds_list = find_list_in_response(listing)
    assert ponds_list is not None and isinstance(ponds_list, list), f"Could not find ponds list in response: {listing}"

    # Check that created pond is in list by id or codigo/nome
    found = False
    for item in ponds_list:
        if not isinstance(item, dict):
            continue
        if "id" in item and str(item["id"]) == str(created_viveiro_id):
            found = True
            break
        if "codigo" in item and item.get("codigo") == pond_payload.get("codigo"):
            found = True
            break
        if "nome" in item and item.get("nome") == pond_payload.get("nome"):
            found = True
            break

    assert found, f"Created pond (id={created_viveiro_id}) not found in ponds list."

    # Verify KPIs exist in listing (common keys: kpis, KPIs, meta.kpis)
    kpis_present = False
    if isinstance(listing, dict):
        for k in ("kpis", "KPIs", "meta", "summary"):
            if k in listing:
                # if meta contains kpis
                if k == "meta" and isinstance(listing[k], dict) and any(x in listing[k] for x in ("kpis", "KPIs")):
                    kpis_present = True
                    break
                if k in listing:
                    kpis_present = True
                    break
    # also check inside data
    if not kpis_present and "data" in listing and isinstance(listing["data"], dict):
        for k in ("kpis", "KPIs", "summary"):
            if k in listing["data"]:
                kpis_present = True
                break

    assert kpis_present, f"KPIs not present in ponds listing response: {listing}"

    # Cleanup: delete created pond
    try:
        del_resp = delete_pond(token, created_viveiro_id)
        # Accept 200, 204, 202 or 404 (if already removed)
        if del_resp.status_code not in (200, 202, 204, 404):
            raise AssertionError(f"Failed to delete created pond (id={created_viveiro_id}), status {del_resp.status_code}: {del_resp.text}")
    except requests.RequestException as e:
        raise AssertionError(f"Error while deleting created pond: {e}")

    print("test_viveiros_management_api_create_and_list_ponds: PASSED")


if __name__ == "__main__":
    try:
        test_viveiros_management_api_create_and_list_ponds()
    except AssertionError as e:
        print("AssertionError:", e)
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(2)