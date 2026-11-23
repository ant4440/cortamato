"""Authentication and password management for Cortamato users."""

import base64
import binascii
import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from decimal import Decimal

from mysql.connector import Error, IntegrityError

from SQL.connection import close_connection, get_connection


PASSWORD_HASH_ITERATIONS = 600_000
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
_PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
_EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    nome: str
    email: str
    foto_perfil: str | None = None


def contar_utilizadores() -> int:
    """Return the number of user profiles stored in the database."""
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM utilizador")
        result = cursor.fetchone()
        if not isinstance(result, tuple) or len(result) != 1:
            raise RuntimeError(
                "The user profile count query returned an invalid result."
            )
        count = result[0]
        if not isinstance(count, (int, Decimal)):
            raise RuntimeError("The user profile count query returned an invalid count.")
        return int(count)
    except Error as exc:
        raise ConnectionError(
            f"Unable to count user profiles in MySQL: {exc}"
        ) from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def is_valid_email(email: str) -> bool:
    """Return whether an email address matches the school's supported format."""
    email = email.strip()
    if len(email) > 254 or ".." in email:
        return False

    local_part, separator, domain = email.rpartition("@")
    return bool(
        separator
        and len(local_part) <= 64
        and not local_part.startswith(".")
        and not local_part.endswith(".")
        and _EMAIL_PATTERN.fullmatch(email)
        and domain
    )


def hash_password(password: str) -> str:
    """Hash a new password with PBKDF2-HMAC-SHA256 and a unique random salt."""
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError("A palavra-passe deve ter entre 8 e 128 caracteres.")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{_PASSWORD_HASH_SCHEME}${PASSWORD_HASH_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a Phase 1 placeholder or a hash created by :func:`hash_password`."""
    if encoded_hash == "x":
        return hmac.compare_digest(password.encode("utf-8"), b"x")
    if not password or len(password) > MAX_PASSWORD_LENGTH:
        return False

    try:
        scheme, iteration_text, salt_text, digest_text = encoded_hash.split("$")
        iterations = int(iteration_text)
        if (
            scheme != _PASSWORD_HASH_SCHEME
            or not 100_000 <= iterations <= PASSWORD_HASH_ITERATIONS
        ):
            return False

        salt = _decode_hash_part(salt_text)
        expected_digest = _decode_hash_part(digest_text)
        if salt is None or len(salt) != 16:
            return False
        if expected_digest is None or len(expected_digest) != 32:
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual_digest, expected_digest)
    except (AttributeError, TypeError, ValueError):
        return False


def _decode_hash_part(value: str) -> bytes | None:
    padded_value = value + "=" * (-len(value) % 4)
    try:
        return base64.b64decode(
            padded_value,
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, binascii.Error):
        return None


def authenticate_user(email: str, password: str) -> AuthenticatedUser | None:
    """Return the active user for valid credentials, otherwise ``None``."""
    email = email.strip()
    if not is_valid_email(email) or not password:
        return None

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, nome, email, password_hash, foto_perfil
            FROM utilizador
            WHERE email = %s AND ativo = TRUE
            """,
            (email,),
        )
        row = cursor.fetchone()
        if row is None or not verify_password(password, row[3]):
            return None
        return AuthenticatedUser(
            id=row[0],
            nome=row[1],
            email=row[2],
            foto_perfil=row[4],
        )
    except Error as exc:
        raise ConnectionError(
            f"Unable to authenticate against MySQL: {exc}"
        ) from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def set_user_password(email: str, password: str) -> None:
    """Set a user's password; intended for the local account setup command."""
    email = email.strip()
    if not is_valid_email(email):
        raise ValueError("Introduza um email válido.")
    encoded_hash = hash_password(password)

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE utilizador
            SET password_hash = %s
            WHERE email = %s AND ativo = TRUE
            """,
            (encoded_hash, email),
        )
        if cursor.rowcount != 1:
            raise LookupError("Não foi encontrada uma conta ativa com esse email.")
    except Error as exc:
        raise ConnectionError(
            f"Unable to update the MySQL account password: {exc}"
        ) from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def change_user_password(
    email: str,
    current_password: str,
    new_password: str,
) -> bool:
    """Change an active user's password only when the current password matches."""
    email = email.strip()
    if not is_valid_email(email):
        raise ValueError("Introduza um email válido.")
    encoded_hash = hash_password(new_password)

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT password_hash
            FROM utilizador
            WHERE email = %s AND ativo = TRUE
            """,
            (email,),
        )
        row = cursor.fetchone()
        if row is None or not verify_password(current_password, row[0]):
            return False

        cursor.execute(
            """
            UPDATE utilizador
            SET password_hash = %s
            WHERE email = %s AND ativo = TRUE AND password_hash = %s
            """,
            (encoded_hash, email, row[0]),
        )
        return cursor.rowcount == 1
    except Error as exc:
        raise ConnectionError(
            f"Unable to update the MySQL account password: {exc}"
        ) from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def change_user_email(
    current_email: str,
    current_password: str,
    new_email: str,
) -> bool:
    """Change an active user's email only when the current password matches."""
    current_email = current_email.strip()
    new_email = new_email.strip()
    if not is_valid_email(new_email):
        raise ValueError("Introduza um email válido.")
    if len(new_email) > 150:
        raise ValueError("O email deve ter até 150 caracteres.")
    if current_email.casefold() == new_email.casefold():
        raise ValueError("O novo email é igual ao atual.")

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT password_hash
            FROM utilizador
            WHERE email = %s AND ativo = TRUE
            """,
            (current_email,),
        )
        row = cursor.fetchone()
        if row is None or not verify_password(current_password, row[0]):
            return False

        cursor.execute(
            """
            UPDATE utilizador
            SET email = %s
            WHERE email = %s AND ativo = TRUE AND password_hash = %s
            """,
            (new_email, current_email, row[0]),
        )
        return cursor.rowcount == 1
    except IntegrityError as exc:
        raise ValueError(
            "Este email já está associado a outra conta."
        ) from exc
    except Error as exc:
        raise ConnectionError(
            f"Unable to update the MySQL account email: {exc}"
        ) from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def update_user_name(user_id: int, name: str) -> bool:
    """Update an active user's display name."""
    name = name.strip()
    if user_id <= 0:
        raise ValueError("O utilizador selecionado é inválido.")
    if not name or len(name) > 150:
        raise ValueError("O nome é obrigatório e deve ter até 150 caracteres.")

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE utilizador
            SET nome = %s
            WHERE id = %s AND ativo = TRUE
            """,
            (name, user_id),
        )
        return cursor.rowcount == 1
    except Error as exc:
        raise ConnectionError(
            f"Unable to update the MySQL account name: {exc}"
        ) from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def update_user_profile_photo(user_id: int, photo_path: str) -> bool:
    """Update an active user's profile photo path."""
    if user_id <= 0:
        raise ValueError("O utilizador selecionado é inválido.")
    if not photo_path or len(photo_path) > 255:
        raise ValueError("O caminho da fotografia de perfil é inválido.")

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE utilizador
            SET foto_perfil = %s
            WHERE id = %s AND ativo = TRUE
            """,
            (photo_path, user_id),
        )
        return cursor.rowcount == 1
    except Error as exc:
        raise ConnectionError(
            f"Unable to update the MySQL profile photo: {exc}"
        ) from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def main() -> None:
    """Prompt locally for a password to provision an existing database account."""
    from getpass import getpass

    email = input("Email da conta: ").strip()
    password = getpass("Nova palavra-passe (mínimo 8 caracteres): ")
    confirmation = getpass("Confirmar palavra-passe: ")
    if password != confirmation:
        raise SystemExit("As palavras-passe não coincidem.")

    try:
        set_user_password(email, password)
    except (ConnectionError, LookupError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Palavra-passe definida para {email}.")


if __name__ == "__main__":
    main()
