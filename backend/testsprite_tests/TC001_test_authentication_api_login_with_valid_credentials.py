import requests
import uuid
import sys
from requests.exceptions import RequestException

BASE_URL = "http://localhost:8000"
REGISTER_PATH = "/api/v1/auth/register"
LOGIN_PATH = "/api/v1/auth/login"
TIMEOUT = 30


def test_authentication_api_login_with_valid_credentials():
    register_url = BASE_URL.rstrip("/") + REGISTER_PATH
    login_url = BASE_URL.rstrip("/") + LOGIN_PATH

    unique_email = f"testuser-{uuid.uuid4().hex[:12]}@example.com"
    password = "TestPass123!"
    register_payload = {
        "email": unique_email,
        "password": password,
        "name": "Test User"
    }
    headers = {"Content-Type": "application/json"}

    user_id = None
    token = None

    try:
        # Register a new user
        try:
            r = requests.post(register_url, json=register_payload, headers=headers, timeout=TIMEOUT)
        except RequestException as e:
            raise AssertionError(f"Failed to call register endpoint: {e}")

        # Accept 201 Created or 200 OK depending on implementation
        assert r.status_code in (200, 201), f"Expected 200 or 201 from register, got {r.status_code}, body: {r.text}"
        try:
            reg_json = r.json()
        except ValueError:
            raise AssertionError(f"Register response is not valid JSON: {r.text}")

        # Attempt to extract user id if provided
        if isinstance(reg_json, dict):
            user_id = reg_json.get("id") or reg_json.get("user", {}).get("id") or reg_json.get("data", {}).get("id")

        # Now login with the created credentials
        login_payload = {"email": unique_email, "password": password}
        try:
            r2 = requests.post(login_url, json=login_payload, headers=headers, timeout=TIMEOUT)
        except RequestException as e:
            raise AssertionError(f"Failed to call login endpoint: {e}")

        assert r2.status_code == 200, f"Expected 200 from login, got {r2.status_code}, body: {r2.text}"
        try:
            login_json = r2.json()
        except ValueError:
            raise AssertionError(f"Login response is not valid JSON: {r2.text}")

        # Accept common token shapes
        token = (
            login_json.get("access_token")
            or login_json.get("token")
            or (login_json.get("data") and login_json.get("data").get("access_token"))
            or (login_json.get("data") and login_json.get("data").get("token"))
        )
        assert token and isinstance(token, str) and len(token) > 0, f"No JWT token found in login response: {login_json}"

        # If token_type provided, ensure it's bearer
        token_type = login_json.get("token_type") or login_json.get("type")
        if token_type:
            assert isinstance(token_type, str) and token_type.lower() == "bearer", f"Expected token_type 'bearer', got: {token_type}"

        print("TC001 passed: login returned 200 and a JWT token")

    finally:
        # Cleanup: best-effort delete the created user if possible
        # Try a few plausible delete endpoints. Use the obtained token for authorization if available.
        if user_id:
            auth_headers = {"Authorization": f"Bearer {token}"} if token else {}
            auth_headers.update({"Content-Type": "application/json"})

            delete_endpoints = [
                f"/api/v1/auth/users/{user_id}",
                f"/api/v1/users/{user_id}",
                f"/api/v1/usuarios/{user_id}",
            ]

            for path in delete_endpoints:
                url = BASE_URL.rstrip("/") + path
                try:
                    resp = requests.delete(url, headers=auth_headers, timeout=TIMEOUT)
                except RequestException:
                    continue
                if resp.status_code in (200, 202, 204):
                    # deleted successfully
                    break
        # Nothing else to do; cleanup was best-effort


if __name__ == "__main__":
    try:
        test_authentication_api_login_with_valid_credentials()
    except AssertionError as e:
        print(f"TC001 failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"TC001 encountered an unexpected error: {e}")
        sys.exit(2)
    sys.exit(0)