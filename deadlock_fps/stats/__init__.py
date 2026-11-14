"""Deadlock statistics: hero meta, rank distribution and one player's own numbers, from the public Deadlock API.

Qt-free, like the other engines. `source.StatsSource` is the entry point; `api` talks to the server, `cache` keeps public
answers on disk, `steam` turns the spellings of a Steam id into the account number the server wants.
"""
