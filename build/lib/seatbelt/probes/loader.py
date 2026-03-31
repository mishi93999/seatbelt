import json
import os
import random
import time
import urllib.request
from pathlib import Path


PRIVATE_PROBES_URL = (
    "https://raw.githubusercontent.com/mishi93999/seatbelt-probes-private/main"
)


class ProbeLoader:
    """
    Merge public (built-in) probes with optional private probes at runtime.

    Private probes are fetched from a private GitHub repo using a token
    and cached locally for 24 hours to avoid repeated network calls.
    """

    def __init__(self, private_token: str | None = None, cache_dir: str | None = None):
        self.token = private_token or os.environ.get("SEATBELT_PRIVATE_TOKEN")
        self.cache_dir = Path(cache_dir or Path.home() / ".seatbelt" / "probe_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load(self, dimension: str, public_probes: list[dict]) -> list[dict]:
        """
        Return public probes plus private probes for this dimension.
        If no private token is present, return public probes as-is.
        """
        if not self.token:
            return public_probes

        private = self._fetch_private(dimension)
        merged = public_probes + private
        random.shuffle(merged)
        return merged

    def _fetch_private(self, dimension: str) -> list[dict]:
        cache_file = self.cache_dir / f"{dimension}_private.json"

        # Use cache if newer than 24 hours.
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < 86_400:
                try:
                    with cache_file.open("r", encoding="utf-8") as f:
                        cached = json.load(f)
                    return self._mark_private(cached) if isinstance(cached, list) else []
                except Exception:
                    pass

        url = f"{PRIVATE_PROBES_URL}/{dimension}/private_probes.json"
        try:
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"token {self.token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                probes = json.loads(resp.read().decode("utf-8"))

            if not isinstance(probes, list):
                return []

            probes = self._mark_private(probes)

            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(probes, f)

            return probes
        except Exception:
            # Fail silently: public probes still run.
            return []

    def _mark_private(self, probes: list[dict]) -> list[dict]:
        for probe in probes:
            if isinstance(probe, dict):
                probe["is_private"] = True
        return probes
