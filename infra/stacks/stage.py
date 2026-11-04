from dataclasses import dataclass

ZONE_NAME = "ukdoshi.com"  # owned by the main site's UkdoshiDns stack; looked up here, never recreated


@dataclass(frozen=True)
class Stage:
    """One copy of the lab: its web address and how open it is."""

    name: str  # "" for live
    site_domain: str
    search_engines: bool = True  # False adds "X-Robots-Tag: noindex" to every response
    password: bool = False  # pages ask for a username and password (set with scripts/site-password.sh)

    def stack_name(self, part: str) -> str:
        return f"UkdoshiLab{self.name.capitalize()}{part}"


# Password-protected and hidden from search engines while the lab is being built.
LIVE = Stage(
    name="",
    site_domain=f"lab.{ZONE_NAME}",
    search_engines=False,
    password=True,
)

STAGING = Stage(
    name="staging",
    site_domain=f"staging.lab.{ZONE_NAME}",
    search_engines=False,
    password=True,
)
