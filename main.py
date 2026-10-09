import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS: dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

app = FastAPI(title="12-Factor Config Precedence API")

# The assignment page must be able to call this API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def coerce(key: str, value: Any) -> Any:
    """Apply the assignment's required output types."""
    if key in ("port", "workers"):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "on"}
    if value is None:
        return ""
    return str(value)

def normalize_layer(layer: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in layer.items():
        key = str(key).strip().lower()
        if key == "num_workers":
            key = "workers"
        normalized[key] = value
    return normalized

def load_effective_config(cli_overrides: list[str]) -> dict[str, Any]:
    config: dict[str, Any] = dict(DEFAULTS)

    # Layer 2: environment-specific YAML.
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as stream:
            yaml_layer = yaml.safe_load(stream) or {}
        if isinstance(yaml_layer, dict):
            config.update(normalize_layer(yaml_layer))

    # Layer 3: .env file. NUM_WORKERS is an assignment-specific alias.
    env_path = BASE_DIR / ".env"
    dotenv_layer = {k: v for k, v in dotenv_values(env_path).items() if v is not None}
    config.update(normalize_layer(dotenv_layer))

    # Layer 4: process/OS environment variables prefixed with APP_.
    os_layer: dict[str, Any] = {}
    for env_key, value in os.environ.items():
        if env_key.startswith("APP_") and env_key != "APP_ENV":
            config_key = env_key[4:].lower()
            os_layer[config_key] = value
    config.update(normalize_layer(os_layer))

    # Highest precedence: repeated query params such as ?set=port=9000&set=debug=true.
    for item in cli_overrides:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key:
            if key == "num_workers":
                key = "workers"
            config[key] = value

    result = {key: coerce(key, value) for key, value in config.items()}
    # Always mask secrets, including secrets supplied as query overrides.
    if "api_key" in result:
        result["api_key"] = "****"
    else:
        result["api_key"] = "****"

    # Guarantee the required five keys even if a layer omits one.
    for key, default in DEFAULTS.items():
        result.setdefault(key, coerce(key, default))
    return result

@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    return load_effective_config(set)

@app.get("/")
def root():
    return {"status": "ok", "endpoint": "/effective-config"}
