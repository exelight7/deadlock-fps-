"""Mod store engine: a local, searchable copy of the Deadlock mod catalogue on GameBanana. Independent of Qt.

    GameBananaClient   reads the public API through a `repos.Transport` (pinned HTTPS, size limits)
    Catalog            SQLite + full-text search; every filter and sort is answered locally
    StoreSync          resumable full crawl and incremental refresh, paced for GameBanana's rate limits

The store never installs anything. Files published on GameBanana carry an MD5 checksum only, so a package taken
from it is never treated as hash-verified (see docs and the vault note "Mod Store").
"""
from .catalog import Catalog
from .gamebanana import GameBananaClient, BAD_RESPONSE
from .model import Category, IndexPage, Profile, QueryResult, StoreFile, Submission
from .sync import StoreSync, SyncReport
