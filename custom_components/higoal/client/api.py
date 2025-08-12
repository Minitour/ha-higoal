from datetime import datetime, timedelta, timezone
import requests

UTC = timezone.utc  # keep using UTC for timestamps
_TOKEN_MAX_AGE = timedelta(hours=1)  # validity window


class Api:
    def __init__(self, domain: str = "server.higoal.net",
                 port: int = 8143,
                 version: str = "V3.21.1",
                 username: str | None = None,
                 password: str | None = None,
                 session: requests.Session | None = None):
        self.session = session or requests.Session()
        self._username = username
        self._password = password
        self._version = version
        self._domain = domain
        self._port = port
        self.url = f"https://{domain}:{port}"

        self.user_id: str | None = None
        self.token: str | None = None
        self.home_ids: list[str] | None = None
        self._sign_in_time: datetime | None = None

    def _token_expired(self) -> bool:
        """Return True if we have a token and it is older than the max age."""
        return (
                self.token is not None
                and self._sign_in_time is not None
                and datetime.now(UTC) - self._sign_in_time > _TOKEN_MAX_AGE
        )

    @property
    def is_signed_in(self) -> bool:
        """Check that we are logged in and the token is still fresh."""
        if self._token_expired():
            self.reset()
            return False
        return bool(self.user_id and self.token and self.home_ids)

    def reset(self):
        self.user_id = None
        self.token = None
        self.home_ids = None
        self._sign_in_time = None  # <- also clear timestamp

    def sign_in(self) -> None:
        """Log in (again) if we are not signed‑in or the token is stale."""
        if self.is_signed_in:  # fresh token => nothing to do
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
            raise RuntimeError("Sign‑in failed: token missing")

        self._sign_in_time = datetime.now(UTC)  # record fresh timestamp


class AsyncApi(Api):

    def __init__(self,
                 domain: str = "server.higoal.net",
                 port: int = 8143,
                 version: str = "V3.21.1",
                 username: str | None = None,
                 password: str | None = None,
                 session=None):
        super().__init__(domain, port, version, username, password, session)
        self.session = session

    async def sign_in(self) -> None:
        """Log in (again) if we are not signed‑in or the token is stale."""
        if self.is_signed_in:  # fresh token => nothing to do
            return

        payload = (
            f"password={self._password}&username={self._username}&ver={self._version}"
        )
        headers = {"content-type": "application/x-www-form-urlencoded; charset=utf-8"}

        response = await self.session.post(f"{self.url}/login", data=payload, headers=headers)
        body = await response.json()

        self.user_id = body.get("repData", {}).get("uid")
        self.token = body.get("repData", {}).get("token")
        self.home_ids = [
            home.get("id") for home in body.get("repData", {}).get("homeList", [])
        ]

        if self.token is None:
            raise RuntimeError("Sign‑in failed: token missing")

        self._sign_in_time = datetime.now(UTC)
