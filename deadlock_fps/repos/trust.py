"""Trust labels.

A label records an actual review decision, so it can only come from a source
the user already trusts: the registry shipped inside the application. It is
never taken from the repository's own index (a publisher cannot grant itself
VERIFIED) and never inferred from where the repository is hosted (a GitHub
address is not trusted because it is on GitHub).

    OFFICIAL    published by the Toolbox project itself
    VERIFIED    reviewed by the Toolbox maintainers: contents inspected, publisher identified
    COMMUNITY   listed as a known community-maintained source, contents not individually reviewed
    UNVERIFIED  everything else, which is every repository a user adds by hand

The registry changes only when the application is updated, so no remote party
can promote a repository by serving new data. If the registry file is
missing or damaged every repository is UNVERIFIED, the safe default.
"""
import json
from pathlib import Path

from .model import Trust

REGISTRY_FILE = Path(__file__).resolve().parents[2] / 'assets' / 'trust' / 'registry.json'
REGISTRY_SCHEMA = 'deadlock-trust-registry'
MAX_REGISTRY_BYTES = 256 * 1024

DESCRIPTIONS = {
    Trust.OFFICIAL: 'Published by the Deadlock Toolbox project.',
    Trust.VERIFIED: 'Reviewed by the Toolbox maintainers.',
    Trust.COMMUNITY: 'A known community-maintained source. Its files have not been individually reviewed.',
    Trust.UNVERIFIED: 'Nobody has reviewed this source. Only install what you trust its author for.',
}


class TrustRegistry:
    def __init__(self, entries=None, problem=''):
        self._entries = dict(entries or {})
        self.problem = problem

    @classmethod
    def load(cls, path=REGISTRY_FILE):
        try:
            path = Path(path)
            if path.stat().st_size > MAX_REGISTRY_BYTES:
                raise ValueError('registry is too large')
            document = json.loads(path.read_text(encoding='utf-8'))
            if document.get('schema') != REGISTRY_SCHEMA or document.get('version') != 1:
                raise ValueError('unknown registry schema')
            entries = {}
            for item in document.get('entries', []):
                label = Trust(item['label'])
                if label is not Trust.UNVERIFIED and isinstance(item.get('repository'), str):
                    entries[item['repository'].lower()] = (label, str(item.get('note', ''))[:300])
            return cls(entries)
        except FileNotFoundError:
            return cls({}, 'trust registry not found; every repository is UNVERIFIED')
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            return cls({}, 'trust registry unreadable (%s); every repository is UNVERIFIED' % error)

    def label_for(self, repository_id):
        """(Trust, note) for a canonical repository id."""
        label, note = self._entries.get(repository_id.lower(), (Trust.UNVERIFIED, ''))
        return label, note or DESCRIPTIONS[label]

    def __len__(self):
        return len(self._entries)
