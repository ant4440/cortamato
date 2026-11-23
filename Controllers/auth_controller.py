"""Authentication controller for user sign-in."""

from Model.auth import (
    AuthenticatedUser,
    authenticate_user,
    change_user_email,
    change_user_password,
    contar_utilizadores,
    update_user_name,
    update_user_profile_photo,
)


class AuthController:
    """Coordinates authentication requests from the view."""

    def authenticate(self, email: str, password: str) -> AuthenticatedUser | None:
        return authenticate_user(email, password)

    def contar_utilizadores(self) -> int:
        return contar_utilizadores()

    def change_password(
        self,
        email: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        return change_user_password(email, current_password, new_password)

    def change_email(
        self,
        current_email: str,
        current_password: str,
        new_email: str,
    ) -> bool:
        return change_user_email(current_email, current_password, new_email)

    def update_profile_name(self, user_id: int, name: str) -> bool:
        return update_user_name(user_id, name)

    def update_profile_photo(self, user_id: int, photo_path: str) -> bool:
        return update_user_profile_photo(user_id, photo_path)
