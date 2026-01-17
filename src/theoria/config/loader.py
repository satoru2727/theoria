from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

GLOBAL_CONFIG_DIR = Path.home() / ".config" / "theoria"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.yaml"
PROJECT_CONFIG_FILES = ["config.theoria.yaml", ".theoria.yaml"]


class ProviderConfig(BaseModel):
    default_model: str | None = None
    api_base: str | None = None
    timeout: int = 120


class AgentConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int | None = None


class BibliographyConfig(BaseModel):
    default_style: str = "apa"
    bib_file: str = "references.bib"


class LatexConfig(BaseModel):
    compiler: str = "pdflatex"
    output_dir: str = "build"


class Config(BaseModel):
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    bibliography: BibliographyConfig = Field(default_factory=BibliographyConfig)
    latex: LatexConfig = Field(default_factory=LatexConfig)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as f:
        data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _find_project_config(start: Path | None = None) -> Path | None:
    cwd = start or Path.cwd()
    for parent in [cwd, *cwd.parents]:
        for name in PROJECT_CONFIG_FILES:
            config_path = parent / name
            if config_path.exists():
                return config_path
    return None


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    if provider := os.environ.get("THEORIA_PROVIDER"):
        config.setdefault("agent", {})["provider"] = provider
    if model := os.environ.get("THEORIA_MODEL"):
        config.setdefault("agent", {})["model"] = model
    if temp := os.environ.get("THEORIA_TEMPERATURE"):
        config.setdefault("agent", {})["temperature"] = float(temp)
    return config


def load_config(project_dir: Path | None = None) -> Config:
    global_data = _load_yaml_file(GLOBAL_CONFIG_FILE)

    project_config_path = _find_project_config(project_dir)
    project_data = _load_yaml_file(project_config_path) if project_config_path else {}

    merged = _deep_merge(global_data, project_data)
    merged = _apply_env_overrides(merged)

    return Config.model_validate(merged)


def save_global_config(config: Config) -> None:
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with GLOBAL_CONFIG_FILE.open("w") as f:
        yaml.dump(config.model_dump(exclude_defaults=True), f, default_flow_style=False)


def init_project_config(path: Path | None = None) -> Path:
    target = (path or Path.cwd()) / "config.theoria.yaml"
    if not target.exists():
        default_config = Config()
        with target.open("w") as f:
            yaml.dump(default_config.model_dump(), f, default_flow_style=False)
    return target
