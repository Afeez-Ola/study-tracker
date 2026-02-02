import os
import secrets
from dataclasses import dataclass
from typing import Optional, List
import yaml


@dataclass
class DatabaseConfig:
    path: str = "study_tracker.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    max_sessions: int = 10000


@dataclass
class SecurityConfig:
    secret_key: str = secrets.token_urlsafe(32)
    cors_origins: List[str] = None
    csrf_enabled: bool = True
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    auth_required: bool = False


@dataclass
class MonitoringConfig:
    idle_threshold_seconds: int = 3
    activity_check_interval_ms: int = 100
    websocket_enabled: bool = True
    activity_log_retention_days: int = 30


@dataclass
class AppConfig:
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 5000
    log_level: str = "INFO"
    environment: str = "development"
    database: DatabaseConfig = None
    security: SecurityConfig = None
    monitoring: MonitoringConfig = None

    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()


class ConfigLoader:
    @staticmethod
    def load_from_file(config_path: str) -> AppConfig:
        """Load configuration from YAML file"""
        if not os.path.exists(config_path):
            return ConfigLoader.load_from_env()

        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            return AppConfig(
                debug=config_data.get("debug", False),
                host=config_data.get("host", "127.0.0.1"),
                port=config_data.get("port", 5000),
                log_level=config_data.get("log_level", "INFO"),
                environment=config_data.get("environment", "development"),
                database=DatabaseConfig(**config_data.get("database", {})),
                security=SecurityConfig(
                    cors_origins=config_data.get("security", {}).get(
                        "cors_origins", ["http://localhost:3000"]
                    ),
                    **{
                        k: v
                        for k, v in config_data.get("security", {}).items()
                        if k != "cors_origins"
                    },
                ),
                monitoring=MonitoringConfig(**config_data.get("monitoring", {})),
            )
        except Exception as e:
            print(f"Error loading config file: {e}")
            return ConfigLoader.load_from_env()

    @staticmethod
    def load_from_env() -> AppConfig:
        """Load configuration from environment variables"""
        return AppConfig(
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
            host=os.getenv("FLASK_HOST", "127.0.0.1"),
            port=int(os.getenv("FLASK_PORT", 5000)),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            environment=os.getenv("FLASK_ENV", "development"),
            database=DatabaseConfig(
                path=os.getenv("DB_PATH", os.path.expanduser("~/study_tracker.db")),
                backup_enabled=os.getenv("DB_BACKUP_ENABLED", "true").lower() == "true",
                backup_interval_hours=int(os.getenv("DB_BACKUP_INTERVAL", 24)),
                max_sessions=int(os.getenv("DB_MAX_SESSIONS", 10000)),
            ),
            security=SecurityConfig(
                secret_key=os.getenv("SECRET_KEY", secrets.token_urlsafe(32)),
                cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(
                    ","
                ),
                csrf_enabled=os.getenv("CSRF_ENABLED", "true").lower() == "true",
                rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower()
                == "true",
                rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", 60)),
                auth_required=os.getenv("AUTH_REQUIRED", "false").lower() == "true",
            ),
            monitoring=MonitoringConfig(
                idle_threshold_seconds=int(os.getenv("IDLE_THRESHOLD_SECONDS", 3)),
                activity_check_interval_ms=int(
                    os.getenv("ACTIVITY_CHECK_INTERVAL_MS", 100)
                ),
                websocket_enabled=os.getenv("WEBSOCKET_ENABLED", "true").lower()
                == "true",
                activity_log_retention_days=int(
                    os.getenv("ACTIVITY_LOG_RETENTION_DAYS", 30)
                ),
            ),
        )

    @staticmethod
    def get_default() -> AppConfig:
        """Get default configuration for development"""
        return ConfigLoader.load_from_env()


# Global configuration instance
config = ConfigLoader.get_default()
