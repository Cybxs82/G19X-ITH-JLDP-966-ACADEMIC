import hashlib
import ipaddress
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

import bcrypt

from ..infrastructure.database import get_db_connection

SESSION_COOKIE = "cfo_session"
SESSION_DAYS = 7


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _valid_ip(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def _audit(cursor: Any, user_id: Optional[UUID], action: str, details: Dict[str, Any]) -> None:
    cursor.execute(
        """
        INSERT INTO registro_auditoria (usuario_id, accion, tipo_entidad, detalles)
        VALUES (%s, %s, %s, %s::jsonb)
        """,
        (str(user_id) if user_id else None, action, "autenticacion", json.dumps(details)),
    )


def _user_payload(row: Any) -> Dict[str, Any]:
    return {
        "id": row[0],
        "email": row[1],
        "full_name": row[2],
        "username": row[3],
        "phone": row[4],
        "role": row[5],
        "is_active": row[6],
    }


def register_user(email: str, full_name: str, password: str, role: str = "analista") -> Dict[str, Any]:
    normalized_email = email.strip().lower()
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if role not in {"cfo", "analista", "administrador"}:
        raise ValueError("Rol no permitido")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM usuarios WHERE lower(correo) = lower(%s)", (normalized_email,))
            if cursor.fetchone() is not None:
                raise ValueError("Ya existe una cuenta con ese correo")
            cursor.execute(
                """
                INSERT INTO usuarios (correo, nombre_completo, rol, esta_activo, correo_verificado)
                VALUES (%s, %s, %s::rol_usuario, TRUE, FALSE)
                RETURNING id, correo, nombre_completo, nombre_usuario, telefono, rol, esta_activo
                """,
                (normalized_email, full_name.strip(), role),
            )
            user = cursor.fetchone()
            cursor.execute(
                "INSERT INTO credenciales_usuario (usuario_id, hash_contrasena) VALUES (%s, %s)",
                (user[0], password_hash),
            )
            _audit(cursor, user[0], "crear_cuenta", {"correo": normalized_email, "rol": role})
            connection.commit()
    return _user_payload(user)


def authenticate_user(email: str, password: str, user_agent: Optional[str], ip_address: Optional[str]) -> Tuple[Dict[str, Any], str]:
    normalized_email = email.strip().lower()
    now = datetime.now(timezone.utc)
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.correo, u.nombre_completo, u.nombre_usuario, u.telefono, u.rol, u.esta_activo,
                       c.hash_contrasena, c.intentos_fallidos_inicio_sesion, c.bloqueado_hasta
                FROM usuarios u
                JOIN credenciales_usuario c ON c.usuario_id = u.id
                WHERE lower(u.correo) = lower(%s)
                """,
                (normalized_email,),
            )
            row = cursor.fetchone()
            if row is None:
                _audit(cursor, None, "inicio_sesion_fallido", {"correo": normalized_email})
                connection.commit()
                raise ValueError("Correo o contraseña incorrectos")
            if not row[6]:
                raise ValueError("La cuenta está desactivada")
            if row[9] is not None and row[9] > now:
                raise ValueError("La cuenta está temporalmente bloqueada")

            if not bcrypt.checkpw(password.encode("utf-8"), row[7].encode("utf-8")):
                attempts = row[8] + 1
                locked_until = now + timedelta(minutes=15) if attempts >= 5 else None
                cursor.execute(
                    """
                    UPDATE credenciales_usuario
                    SET intentos_fallidos_inicio_sesion = %s, bloqueado_hasta = %s, actualizado_en = %s
                    WHERE usuario_id = %s
                    """,
                    (0 if locked_until else attempts, locked_until, now, row[0]),
                )
                _audit(cursor, row[0], "inicio_sesion_fallido", {"intentos": attempts})
                connection.commit()
                raise ValueError("Correo o contraseña incorrectos")

            token = secrets.token_urlsafe(48)
            expires_at = now + timedelta(days=SESSION_DAYS)
            cursor.execute(
                """
                INSERT INTO sesiones_autenticacion
                    (usuario_id, hash_token, agente_usuario, direccion_ip, expira_en)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (row[0], _hash_session_token(token), user_agent, _valid_ip(ip_address), expires_at),
            )
            cursor.execute(
                """
                UPDATE credenciales_usuario
                SET intentos_fallidos_inicio_sesion = 0,
                    bloqueado_hasta = NULL,
                    ultimo_inicio_sesion_en = %s,
                    actualizado_en = %s
                WHERE usuario_id = %s
                """,
                (now, now, row[0]),
            )
            _audit(cursor, row[0], "inicio_sesion", {"correo": normalized_email})
            connection.commit()
    return _user_payload(row), token


def get_session_user(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.correo, u.nombre_completo, u.nombre_usuario, u.telefono, u.rol, u.esta_activo
                FROM sesiones_autenticacion s
                JOIN usuarios u ON u.id = s.usuario_id
                WHERE s.hash_token = %s
                  AND s.revocado_en IS NULL
                  AND s.expira_en > now()
                  AND u.esta_activo = TRUE
                """,
                (_hash_session_token(token),),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute(
                "UPDATE sesiones_autenticacion SET ultimo_acceso_en = now() WHERE hash_token = %s",
                (_hash_session_token(token),),
            )
            connection.commit()
            return _user_payload(row)


def update_profile(user_id: UUID, email: str, full_name: str, username: Optional[str], phone: Optional[str], current_password: Optional[str], new_password: Optional[str]) -> Dict[str, Any]:
    normalized_email = email.strip().lower()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.correo, u.nombre_completo, u.nombre_usuario, u.telefono, u.rol, u.esta_activo, c.hash_contrasena
                FROM usuarios u JOIN credenciales_usuario c ON c.usuario_id = u.id
                WHERE u.id = %s
                """,
                (str(user_id),),
            )
            row = cursor.fetchone()
            if row is None or not row[6]:
                raise ValueError("La cuenta no está disponible")
            cursor.execute("SELECT id FROM usuarios WHERE lower(correo) = lower(%s) AND id <> %s", (normalized_email, str(user_id)))
            if cursor.fetchone() is not None:
                raise ValueError("Ya existe una cuenta con ese correo")
            if username:
                cursor.execute("SELECT id FROM usuarios WHERE lower(nombre_usuario) = lower(%s) AND id <> %s", (username.strip(), str(user_id)))
                if cursor.fetchone() is not None:
                    raise ValueError("Ese nombre de usuario ya está ocupado")
            sensitive_change = normalized_email != row[1] or new_password is not None
            if sensitive_change and (not current_password or not bcrypt.checkpw(current_password.encode("utf-8"), row[7].encode("utf-8"))):
                raise ValueError("La contraseña actual es necesaria para cambiar datos sensibles")
            cursor.execute(
                "UPDATE usuarios SET correo = %s, nombre_completo = %s, nombre_usuario = %s, telefono = %s WHERE id = %s RETURNING id, correo, nombre_completo, nombre_usuario, telefono, rol, esta_activo",
                (normalized_email, full_name.strip(), username.strip() if username else None, phone.strip() if phone else None, str(user_id)),
            )
            updated = cursor.fetchone()
            if new_password:
                cursor.execute("UPDATE credenciales_usuario SET hash_contrasena = %s, contrasena_cambiada_en = now() WHERE usuario_id = %s", (bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"), str(user_id)))
            _audit(cursor, user_id, "actualizar_perfil", {"correo": normalized_email, "cambio_contrasena": new_password is not None})
            connection.commit()
    return _user_payload(updated)


def revoke_session(token: Optional[str]) -> None:
    if not token:
        return
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE sesiones_autenticacion SET revocado_en = now() WHERE hash_token = %s AND revocado_en IS NULL",
                (_hash_session_token(token),),
            )
            connection.commit()
