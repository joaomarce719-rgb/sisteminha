import requests
import uuid
import datetime
import sys

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def test_auditoria_api_query_audit_log_entries():
    # Prepare unique test user
    unique = uuid.uuid4().hex[:8]
    email = f"test_audit_{unique}@example.com"
    password = "TestPass123!"
    register_url = f"{BASE_URL}/api/v1/auth/register"
    login_url = f"{BASE_URL}/api/v1/auth/login"
    auditoria_url = f"{BASE_URL}/api/v1/auditoria/"

    user_id = None
    token = None

    # Register user
    try:
        resp = requests.post(
            register_url,
            json={"name": "Test Auditoria User", "email": email, "password": password},
            timeout=TIMEOUT,
        )
    except Exception as e:
        raise AssertionError(f"Failed to call register endpoint: {e}")

    assert resp.status_code in (200, 201), f"Registration failed: {resp.status_code}, {resp.text}"
    try:
        reg_json = resp.json()
    except ValueError:
        reg_json = {}
    # Try to capture any returned user id
    user_id = reg_json.get("id") or reg_json.get("user_id") or reg_json.get("uuid")

    # Login to obtain token
    try:
        resp = requests.post(
            login_url,
            json={"email": email, "password": password},
            timeout=TIMEOUT,
        )
    except Exception as e:
        raise AssertionError(f"Failed to call login endpoint: {e}")

    assert resp.status_code == 200, f"Login failed: {resp.status_code}, {resp.text}"
    try:
        login_json = resp.json()
    except ValueError:
        raise AssertionError("Login response was not valid JSON")

    # Extract token from common fields
    token = login_json.get("access_token") or login_json.get("token") or login_json.get("accessToken") or login_json.get("jwt")
    if not token:
        # Some APIs nest token under data or result
        if isinstance(login_json.get("data"), dict):
            token = login_json["data"].get("access_token") or login_json["data"].get("token")
    assert token, f"Auth token not found in login response: {login_json}"

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    try:
        # 1) Access without token should return 401/403
        try:
            resp_unauth = requests.get(auditoria_url, timeout=TIMEOUT)
        except Exception as e:
            raise AssertionError(f"Failed unauthenticated request to auditoria: {e}")
        assert resp_unauth.status_code in (401, 403), f"Expected 401/403 for unauthenticated request, got {resp_unauth.status_code}"

        # 2) GET /api/v1/auditoria/ without filters (authenticated) -> 200 + JSON (list or paginated dict)
        try:
            resp_all = requests.get(auditoria_url, headers=headers, timeout=TIMEOUT)
        except Exception as e:
            raise AssertionError(f"Failed authenticated request to auditoria: {e}")
        assert resp_all.status_code == 200, f"Authenticated auditoria list failed: {resp_all.status_code}, {resp_all.text}"
        try:
            all_json = resp_all.json()
        except ValueError:
            raise AssertionError("Auditoria response was not valid JSON")
        assert isinstance(all_json, (list, dict)), "Auditoria response JSON should be a list or dict"

        # 3) GET with action filter
        params_action = {"action": "CREATE"}
        try:
            resp_action = requests.get(auditoria_url, headers=headers, params=params_action, timeout=TIMEOUT)
        except Exception as e:
            raise AssertionError(f"Failed auditoria request with action filter: {e}")
        assert resp_action.status_code == 200, f"Auditoria filter by action failed: {resp_action.status_code}, {resp_action.text}"
        try:
            action_json = resp_action.json()
        except ValueError:
            raise AssertionError("Auditoria action-filter response was not valid JSON")
        assert isinstance(action_json, (list, dict)), "Action-filtered auditoria response JSON should be a list or dict"

        # 4) GET with entity filter
        params_entity = {"entity": "viveiro"}
        try:
            resp_entity = requests.get(auditoria_url, headers=headers, params=params_entity, timeout=TIMEOUT)
        except Exception as e:
            raise AssertionError(f"Failed auditoria request with entity filter: {e}")
        assert resp_entity.status_code == 200, f"Auditoria filter by entity failed: {resp_entity.status_code}, {resp_entity.text}"
        try:
            entity_json = resp_entity.json()
        except ValueError:
            raise AssertionError("Auditoria entity-filter response was not valid JSON")
        assert isinstance(entity_json, (list, dict)), "Entity-filtered auditoria response JSON should be a list or dict"

        # 5) GET with date range filter
        today = datetime.datetime.utcnow().date()
        seven_days_ago = today - datetime.timedelta(days=7)
        params_date = {"date_from": seven_days_ago.isoformat(), "date_to": today.isoformat()}
        try:
            resp_date = requests.get(auditoria_url, headers=headers, params=params_date, timeout=TIMEOUT)
        except Exception as e:
            raise AssertionError(f"Failed auditoria request with date range filter: {e}")
        assert resp_date.status_code == 200, f"Auditoria filter by date range failed: {resp_date.status_code}, {resp_date.text}"
        try:
            date_json = resp_date.json()
        except ValueError:
            raise AssertionError("Auditoria date-range response was not valid JSON")
        assert isinstance(date_json, (list, dict)), "Date-range filtered auditoria response JSON should be a list or dict"

        # Optional: Basic content checks if dict (paginated)
        def validate_page_structure(obj):
            if isinstance(obj, dict):
                # acceptable keys commonly used: items, results, data, total, page
                keys = set(obj.keys())
                assert keys & {"items", "results", "data", "total", "page", "count"} , f"Unexpected paginated auditoria response keys: {keys}"

        validate_page_structure(all_json)
        validate_page_structure(action_json)
        validate_page_structure(entity_json)
        validate_page_structure(date_json)

    finally:
        # Try to clean up created user if API supports deletion.
        if user_id:
            delete_user_url = f"{BASE_URL}/api/v1/auth/users/{user_id}"
            try:
                # Attempt with authentication (some systems require admin; this may 403/404 which we ignore)
                requests.delete(delete_user_url, headers=headers, timeout=TIMEOUT)
            except Exception:
                pass


if __name__ == "__main__":
    try:
        test_auditoria_api_query_audit_log_entries()
        print("TC008 passed")
    except AssertionError as e:
        print("TC008 failed:", e)
        sys.exit(1)
    except Exception as e:
        print("TC008 error:", e)
        sys.exit(2)