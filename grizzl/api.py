from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests

from grizzl.config import LOG_ENDPOINT, REQUEST_TIMEOUT_SECONDS


class ChargerAPIError(RuntimeError):
    """Raised when communication with a charger fails."""


@dataclass(frozen=True)
class ChargerResponse:
    """Normalized response returned by the charger API client."""

    status_code: int
    url: str
    content_type: str
    data: Any


class ChargerClient:
    """HTTP client for a single configured Grizzl-E charger."""

    def __init__(
        self,
        charger: dict,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
        session: requests.Session | None = None,
    ) -> None:
        self.charger = charger
        self.charger_id = str(charger["id"])
        self.ssid = str(charger["ssid"])
        self.base_url = str(
            charger.get("target_url") or charger["url"]
        ).rstrip("/") + "/"
        self.timeout = timeout
        self.session = session or requests.Session()

    def _url(self, endpoint: str = "") -> str:
        return urljoin(self.base_url, endpoint.lstrip("/"))

    def _request(
        self,
        method: str,
        endpoint: str = "",
        **kwargs: Any,
    ) -> requests.Response:
        url = self._url(endpoint)

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.Timeout as exc:
            raise ChargerAPIError(
                f"{self.charger_id} timed out after {self.timeout} seconds "
                f"while requesting {url}"
            ) from exc
        except requests.ConnectionError as exc:
            raise ChargerAPIError(
                f"Unable to connect to {self.charger_id} at {url}"
            ) from exc
        except requests.HTTPError as exc:
            status_code = (
                exc.response.status_code
                if exc.response is not None
                else "unknown"
            )
            raise ChargerAPIError(
                f"{self.charger_id} returned HTTP {status_code} for {url}"
            ) from exc
        except requests.RequestException as exc:
            raise ChargerAPIError(
                f"Request to {self.charger_id} failed: {exc}"
            ) from exc

    @staticmethod
    def _decode_response(response: requests.Response) -> Any:
        content_type = response.headers.get("Content-Type", "").lower()

        if "application/json" in content_type:
            try:
                return response.json()
            except ValueError as exc:
                raise ChargerAPIError(
                    f"Charger returned invalid JSON from {response.url}"
                ) from exc

        text = response.text.strip()

        if not text:
            return None

        try:
            return response.json()
        except ValueError:
            return text

    def request(
        self,
        endpoint: str = "",
        method: str = "GET",
        **kwargs: Any,
    ) -> ChargerResponse:
        """Send a request and return a normalized charger response."""
        response = self._request(method, endpoint, **kwargs)

        return ChargerResponse(
            status_code=response.status_code,
            url=response.url,
            content_type=response.headers.get("Content-Type", ""),
            data=self._decode_response(response),
        )

    def status(self) -> dict[str, Any]:
        """Probe the charger and return basic reachability information."""
        response = self.request()

        return {
            "charger_id": self.charger_id,
            "ssid": self.ssid,
            "url": response.url,
            "online": True,
            "http_status": response.status_code,
            "content_type": response.content_type,
        }

    def sessions(self) -> Any:
        """Download the charger's session-log result."""
        return self.request(LOG_ENDPOINT, method="POST").data

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> ChargerClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
