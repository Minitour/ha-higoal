from datetime import datetime, UTC
import requests


class Api:

    def __init__(self, domain: str = "server.higoal.net",
                 port: int = 8143,
                 version: str = "V3.21.1",
                 username: str = None,
                 password: str = None,
                 session: requests.Session = None):
        self.session = session or requests.Session()
        self._username = username
        self._password = password
        self._version = version
        self._domain = domain
        self._port = port
        self.url = f"https://{domain}:{port}"
        self.user_id = None
        self.token = None
        self.home_ids = None
        self._sign_in_time = None

    @property
    def is_signed_in(self):
        return self.user_id and self.token and self.home_ids

    def sign_in(self):
        """Perform log-in with the provided credentials."""
        if self.is_signed_in:
            return

        payload = (
            f"password={self._password}&username={self._username}&ver={self._version}"
        )
        headers = {"content-type": "application/x-www-form-urlencoded; charset=utf-8"}
        response = self.session.request(
            "POST", f"{self.url}/login", data=payload, headers=headers
        )
        body = response.json()
        self.user_id = body.get("repData", {}).get("uid")
        self.token = body.get("repData", {}).get("token")
        self.home_ids = [
            home.get("id") for home in body.get("repData", {}).get("homeList", [])
        ]
        if self.token is None:
            raise Exception("Log-in failed")
        self._sign_in_time = datetime.now(UTC)
