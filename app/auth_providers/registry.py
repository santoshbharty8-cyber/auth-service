from typing import Dict
from app.auth_providers.base import BaseAuthProvider


class AuthProviderRegistry:
    """
    Registry that stores all authentication providers.
    """

    def __init__(self):
        self.providers: Dict[str, BaseAuthProvider] = {}

    def register(self, name: str, provider: BaseAuthProvider):
        """
        Register a provider.

        Example:
            registry.register("password", PasswordAuthProvider(...))
        """

        if name in self.providers:
            raise ValueError(f"Provider {name} already registered")

        self.providers[name] = provider

    def get_provider(self, name: str) -> BaseAuthProvider | None:
        """
        Get provider by name.
        """

        return self.providers.get(name)

    def list_providers(self):

        return list(self.providers.keys())