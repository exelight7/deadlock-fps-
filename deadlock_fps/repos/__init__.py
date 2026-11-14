"""Multi-repository mod catalogue engine.

Independent of Qt and of the installer. Entry points:

    RepositoryManager   add / import / refresh / search repositories
    parse_index         validate a repository index document (the specification, in code)
    Transport           HTTP access, replaceable in tests
    default_registry    the built-in providers (GitHub, GitLab, custom HTTPS)

Specification for repository authors: docs/REPOSITORY_SPEC.md
"""
from .errors import RepoError
from .manager import RepositoryManager, ImportResult
from .model import Compat, Trust, GameFit, RepositoryView, RepositorySource, SearchHit
from .providers import default_registry, ProviderRegistry, Provider
from .spec import parse_index, SCHEMA, SUPPORTED_MAJOR
from .store import RepositoryStore
from .transport import Transport, UrllibTransport, Response
from .trust import TrustRegistry
