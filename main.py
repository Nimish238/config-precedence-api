import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

app = FastAPI(title="Config Precedence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_key(key: str) -> str:
    key = key.strip()

    if key.startswith("APP_"):
        key = key[4:]

    key = key.lower()

    if key == "num_workers":
        key = "workers"

    return key


def coerce(key: str, value: Any) -> Any:
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {
            "true", "1", "yes", "on"
        }

    return str(value)


def effective_config(overrides: list[str]) -> dict:
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"

    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

        if isinstance(yaml_data, dict):
            for key, value in yaml_data.items():
                config[normalize_key(key)] = value

    # Layer 3: .env file
    env_path = BASE_DIR / ".env"
    dotenv_data = dotenv_values(env_path)

    for key, value in dotenv_data.items():
        if value is not None:
            config[normalize_key(key)] = value

    # Layer 4: OS environment variables
    for key, value in os.environ.items():
        if key.startswith("APP_") and key != "APP_ENV":
            config[normalize_key(key)] = value

    # Layer 5: CLI query overrides
    for item in overrides:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)

        if key:
            config[key] = value

    # Guarantee all five required keys exist.
    for key, default_value in DEFAULTS.items():
        if key not in config or config[key] is None:
            config[key] = default_value

    # Convert values to the required types.
    result = {}
    for key, default_value in DEFAULTS.items():
        try:
            result[key] = coerce(key, config[key])
        except (TypeError, ValueError):
            result[key] = default_value

    # Never expose the actual API key.
    result["api_key"] = "****"

    return result


@app.get("/")
def root():
    return {"status": "ok", "endpoint": "/effective-config"}


@app.get("/effective-config")
def get_effective_config(set: list[str] = Query(default=[])):
    return effective_config(set)
