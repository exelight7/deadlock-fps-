"""Catalogue search across repositories. Pure functions over already-loaded indexes."""
import re

from .model import SearchHit, Trust

SORTS = ('relevance', 'name', 'updated', 'repository', 'size')
_TRUST_ORDER = {Trust.OFFICIAL: 0, Trust.VERIFIED: 1, Trust.COMMUNITY: 2, Trust.UNVERIFIED: 3}


def tokens(query):
    return [t for t in re.split(r'\s+', (query or '').lower().strip()) if t]


def score(mod, words):
    """Weighted match score; 0 means at least one word is absent, so the mod is not a hit."""
    if not words:
        return 1.0
    fields = (
        (5.0, mod.name.lower()), (4.0, mod.id), (3.0, ' '.join(mod.categories + mod.tags)),
        (2.0, mod.author.lower()), (1.0, (mod.summary + ' ' + mod.description).lower()))
    total = 0.0
    for word in words:
        best = max((weight * (1.5 if text.startswith(word) else 1.0) for weight, text in fields if word in text), default=0.0)
        if not best:
            return 0.0
        total += best
    return total


def latest_stamp(hit):
    version = hit.latest
    return (version.published if version else '') or hit.mod.published or ''


def search(views_and_indexes, query='', *, category='', repository='', trust=None, installable_only=False, sort='relevance'):
    """views_and_indexes: iterable of (RepositoryView, RepositoryIndex). Returns a list of SearchHit."""
    words = tokens(query)
    category = category.lower().strip()
    hits = []
    for view, index in views_and_indexes:
        if repository and view.source.id != repository:
            continue
        if trust is not None and view.trust != trust:
            continue
        for mod in index.mods:
            if category and category not in mod.categories:
                continue
            latest = mod.latest()
            if installable_only and not (latest and latest.installable):
                continue
            points = score(mod, words)
            if points:
                hits.append(SearchHit(view, mod, latest, points))
    if sort == 'name':
        hits.sort(key=lambda h: (h.mod.name.lower(), h.repository.name.lower()))
    elif sort == 'updated':
        hits.sort(key=lambda h: (latest_stamp(h), h.mod.name.lower()), reverse=True)
    elif sort == 'repository':
        hits.sort(key=lambda h: (h.repository.name.lower(), h.mod.name.lower()))
    elif sort == 'size':
        hits.sort(key=lambda h: ((h.latest.package.size or 0) if h.latest and h.latest.package else 0, h.mod.name.lower()), reverse=True)
    else:
        # Relevance first, then more-trusted sources, then alphabetical: stable and explainable.
        hits.sort(key=lambda h: (-h.score, _TRUST_ORDER[h.repository.trust], h.mod.name.lower()))
    return hits


def categories(views_and_indexes):
    """Category → number of mods, over everything given."""
    counts = {}
    for _, index in views_and_indexes:
        for mod in index.mods:
            for name in mod.categories:
                counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
