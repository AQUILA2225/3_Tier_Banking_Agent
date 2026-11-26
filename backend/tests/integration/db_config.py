from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


BASE_DIR = Path(__file__).resolve().parents[3]


class TestDatabaseSettings(BaseSettings):

    test_db_host: str = "localhost"

    test_db_port: int = Field(
        default=5432,
        ge=1,
        le=65535
    )

    test_db_name: str = "banking_agent_test_db"

    test_db_user: str = "banking_test_app"

    test_db_password: SecretStr = Field(min_length=1)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env.test",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def database_url(self) -> URL:

        if (
            self.test_db_name != "banking_agent_test_db"
            or self.test_db_user != "banking_test_app"
            or self.test_db_host not in ("localhost", "127.0.0.1")
        ):
            raise RuntimeError(
                "Unsafe test database configuration."
            )

        return URL.create(
            drivername="postgresql+psycopg",
            username=self.test_db_user,
            password=self.test_db_password.get_secret_value(),
            host=self.test_db_host,
            port=self.test_db_port,
            database=self.test_db_name
        )