from abc import ABC, abstractmethod
from app.models import User


class BaseAuthProvider(ABC):
    """
    Base interface for all authentication providers.
    """

    @abstractmethod
    def authenticate(self, data: dict) -> User | None:
        """
        Authenticate user based on provider logic.

        Returns:
            User object if authentication succeeds
            None if authentication fails
        """
        pass