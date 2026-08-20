"""Configuration management module."""

import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field


class SearchConfig(BaseModel):
    queries: List[str]
    locations: List[str]
    distance_miles: int = 35
    results_per_query: int = 15
    hours_old: int = 72


class FiltersConfig(BaseModel):
    require_jd: bool = True
    min_experience_years: int = 1
    max_experience_years: int = 3
    target_keywords: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    to_email: str = ""


class WebhookConfig(BaseModel):
    enabled: bool = False
    url: str = ""


class DigestConfig(BaseModel):
    save_html: bool = True
    output_dir: str = "data/digests"


class NotificationsConfig(BaseModel):
    email: EmailConfig = Field(default_factory=EmailConfig)
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)
    digest: DigestConfig = Field(default_factory=DigestConfig)


class DatabaseConfig(BaseModel):
    path: str = "data/jobs.db"


class AppConfig(BaseModel):
    search: SearchConfig
    filters: FiltersConfig
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from config.yaml or specified path."""
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config.yaml")

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found at: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return AppConfig(**data)
