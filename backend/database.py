from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional, Tuple

from dotenv import load_dotenv

from .config import get_settings


load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)


def _psycopg_url(database_url: str) -> str:
    """Convierte la URL de configuracion al formato aceptado por psycopg2."""
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1).replace("postgresql+psycopg2://", "postgresql://", 1)


@contextmanager
def get_db_connection() -> Generator[Any, None, None]:
    """Abre una conexion por operacion y la cierra siempre al terminar."""
    import psycopg2

    settings = get_settings()
    connection = psycopg2.connect(_psycopg_url(settings.database_url), connect_timeout=settings.database_connect_timeout)
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def check_database_connection() -> Tuple[bool, Optional[str]]:
    """Verifica conectividad sin dejar una conexion abierta."""
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        return True, None
    except Exception as error:
        message = str(error) or error.__class__.__name__
        return False, message
