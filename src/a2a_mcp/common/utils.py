# type: ignore
"""Shared utilities for OpenAI-compatible clients, logging, and MCP config."""

import logging
import os
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)
_ENV_BOOTSTRAPPED = False


class OpenAIConfig(BaseModel):
    """OpenAI-compatible API configuration."""

    api_key: str
    base_url: str


class ServerConfig(BaseModel):
    """MCP server connection settings."""

    host: str
    port: int
    transport: str
    url: str


DEFAULT_LLM_MODEL = "deepseek-ai/DeepSeek-V3"


def _dotenv_candidates() -> list[Path]:
    project_root = Path(__file__).resolve().parents[3]
    candidates = [
        Path.cwd() / ".env",
        project_root / ".env",
    ]

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def _load_dotenv_file(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()

        key, sep, value = line.partition("=")
        if not sep:
            continue

        env_name = key.strip()
        if not env_name or env_name in os.environ:
            continue

        os.environ[env_name] = _clean_env_value(value)


def _bootstrap_env() -> None:
    global _ENV_BOOTSTRAPPED
    if _ENV_BOOTSTRAPPED:
        return

    for path in _dotenv_candidates():
        if path.is_file():
            _load_dotenv_file(path)
            break

    _ENV_BOOTSTRAPPED = True


def _clean_env_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1].strip()
    return cleaned


def _get_optional_env(name: str) -> str | None:
    _bootstrap_env()
    raw = os.getenv(name)
    if raw is None:
        return None
    value = _clean_env_value(raw)
    return value or None


def _require_env(name: str) -> str:
    value = _get_optional_env(name)
    if value:
        return value
    raise ValueError(f"{name} is required and must be set in the environment.")


def _require_int_env(name: str) -> int:
    value = _require_env(name)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}.") from exc


def get_llm_model() -> str:
    """Read the model id from OPENAI_MODEL, falling back to the project default."""

    return _get_optional_env("OPENAI_MODEL") or DEFAULT_LLM_MODEL


def get_openai_config() -> OpenAIConfig:
    """Load OpenAI-compatible API settings from the environment."""

    return OpenAIConfig(
        api_key=_require_env("OPENAI_API_KEY"),
        base_url=_require_env("OPENAI_BASE_URL"),
    )


def get_langchain_openai_kwargs() -> dict[str, str]:
    """Return kwargs shared by LangChain ChatOpenAI clients."""

    config = get_openai_config()
    return {
        "openai_api_key": config.api_key,
        "openai_api_base": config.base_url,
    }


def get_openai_env_vars() -> dict[str, str]:
    """Return validated OpenAI-related env vars for subprocesses."""

    config = get_openai_config()
    env = {
        "OPENAI_API_KEY": config.api_key,
        "OPENAI_BASE_URL": config.base_url,
    }
    model = _get_optional_env("OPENAI_MODEL")
    if model:
        env["OPENAI_MODEL"] = model
    return env


def init_api_key() -> OpenAI:
    """Create an OpenAI-compatible client using environment variables only."""

    config = get_openai_config()
    return OpenAI(api_key=config.api_key, base_url=config.base_url)


def config_logging():
    """Configure the root logging level."""

    log_level = (
        _get_optional_env("A2A_LOG_LEVEL")
        or _get_optional_env("FASTMCP_LOG_LEVEL")
        or "INFO"
    ).upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))


def config_logger(logger: logging.Logger):
    """Attach a simple console handler to an individual logger."""

    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(console_handler)


def get_mcp_server_config() -> ServerConfig:
    """Load MCP server settings from the environment."""

    transport = _require_env("MCP_TRANSPORT").lower()
    if transport not in {"sse", "stdio"}:
        raise ValueError("MCP_TRANSPORT must be either 'sse' or 'stdio'.")

    if transport == "sse":
        host = _require_env("MCP_HOST")
        port = _require_int_env("MCP_PORT")
        return ServerConfig(
            host=host,
            port=port,
            transport=transport,
            url=f"http://{host}:{port}/sse",
        )

    return ServerConfig(
        host="",
        port=0,
        transport=transport,
        url="stdio",
    )
