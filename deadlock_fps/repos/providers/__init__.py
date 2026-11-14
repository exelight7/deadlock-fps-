"""Built-in providers and the default registry."""
from .base import Provider, ProviderRegistry, Identity, SyncResult, INDEX_FILENAME
from .github import GitHubProvider
from .gitlab import GitLabProvider
from .native import NativeHttpsProvider


def default_registry():
    """GitHub and GitLab first (they recognise only their own URLs); the custom-HTTPS provider accepts the rest."""
    return ProviderRegistry([GitHubProvider(), GitLabProvider(), NativeHttpsProvider()])
