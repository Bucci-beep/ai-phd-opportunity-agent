from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_role_key: str


def load_settings() -> Settings:
    """
    Load backend application configuration.

    Service role credentials must only be used by trusted server side
    processes and must never be exposed to frontend code.
    """

    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY"
    )

    missing: list[str] = []

    if not supabase_url:
        missing.append("SUPABASE_URL")

    if not service_role_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing:
        names = ", ".join(missing)

        raise RuntimeError(
            f"Missing required environment variables: {names}"
        )

    return Settings(
        supabase_url=supabase_url,
        supabase_service_role_key=service_role_key,
    )
