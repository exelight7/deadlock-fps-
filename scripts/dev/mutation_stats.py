"""Mutation spot-check of the stats feature. Usage: mutation_stats.py <repo root> [words]

With words, only the mutations whose description contains one of them are run.

Breaks one check at a time (Steam id parsing, the formulas, the API client, the cache, the source, the page and the
service), runs `tests/test_stats_*.py`, and reports whether the tests noticed. Each file is restored in a `finally`; do not
run other work in the tree while it runs. A SURVIVED line is a check the tests cannot see.
"""
import os
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
py = root / '.venv' / 'Scripts' / 'python.exe'
if not py.exists():
    py = Path(sys.executable)
app = root / 'deadlock_fps'
steam, maths, api, cache, source = (app / 'stats' / name for name in ('steam.py', 'maths.py', 'api.py', 'cache.py', 'source.py'))
page, service, window = app / 'pages' / 'stats.py', app / 'stats_service.py', app / 'game_link.py'

MUTATIONS = [
    # Steam ids
    ('a vanity address is reported as a plain format problem', steam, "raise SteamIdError('vanity',", "raise SteamIdError('format',"),
    ('any host is accepted for a profile address', steam, " or host not in ('steamcommunity.com', 'www.steamcommunity.com')", ''),
    ('a 64-bit id is not converted', steam, 'number - STEAM64_BASE if number >= STEAM64_BASE else number', 'number'),
    ('the account range is not checked', steam, 'if not 1 <= number <= MAX_ACCOUNT:', 'if False:'),
    ('non-ASCII digits are accepted', steam, 'if not (text.isascii() and text.isdigit()):', 'if not text.isdigit():'),
    ('a userdata folder with a huge number is accepted', steam, 'candidate.isascii() and candidate.isdigit() and 1 <= int(candidate) <= MAX_ACCOUNT', 'candidate.isdigit()'),
    # formulas
    ('Wilson uses 90 % instead of 95 %', maths, 'def wilson(wins, matches, z=1.96):', 'def wilson(wins, matches, z=1.64):'),
    ('KDA divides by zero deaths', maths, 'max(1, deaths)', 'deaths'),
    ('Wilson trusts wins above matches', maths, 'wins = min(max(wins, 0), matches)', 'wins = wins'),
    ('a rate with no whole divides by zero', maths, 'return part / whole if whole else 0.0', 'return part / whole'),
    # the client
    ('a rank tier starts at the wrong badge', api, 'return tier * 10 + 1, tier * 10 + 6', 'return tier * 10, tier * 10 + 6'),
    ('rows with more wins than matches are kept', api, 'if ident <= 0 or matches <= 0 or wins > matches or ident in heroes:', 'if ident <= 0 or matches <= 0 or ident in heroes:'),
    ('rows about other players are kept', api, "to_int(row.get('account_id'), -1) != account_id or ", ''),
    ('the timestamp is not rounded to the hour', api, "int(self.clock()) // 3600 * 3600 - window_days * 86400, 'game_mode': 'normal'}", "int(self.clock()) - window_days * 86400, 'game_mode': 'normal'}"),
    ('the account number is not validated', api, 'if not isinstance(account_id, int) or isinstance(account_id, bool) or not 1 <= account_id <= MAX_ACCOUNT:', 'if False:'),
    ('a rate limit is reported as a network error', api, 'if response.status == 429:', 'if response.status == 4290:'),
    ('a player with no rank is an error', api, '            if error.code == NOT_FOUND:\n                return None', '            if False:\n                return None'),
    ('a JSON nesting bomb crashes', api, 'except (ValueError, UnicodeDecodeError, RecursionError):', 'except (ValueError, UnicodeDecodeError):'),
    ('impossible badges are counted', api, 'if 1 <= tier <= 11 and 1 <= badge % 10 <= 6:', 'if 1 <= tier <= 11:'),
    ('a huge list is not cut', api, 'for row in document[:MAX_ROWS] if isinstance(row, dict)', 'for row in document if isinstance(row, dict)'),
    ('the mode is always sent', api, "        if mode:\n            params['match_mode'] = mode\n        if tier:", "        params['match_mode'] = mode\n        if tier:"),
    # the cache
    ('the cache ignores its age limit', cache, 'return (data, saved) if 0 <= now - saved <= ttl else None', 'return (data, saved)'),
    ('a copy from the future is accepted', cache, '0 <= now - saved <= ttl', 'now - saved <= ttl'),
    ('cache keys are not checked', cache, 'if not _KEY.fullmatch(key):', 'if False:'),
    ('the cache file size is not limited', cache, 'if path.stat().st_size > MAX_FILE:', 'if False:'),
    ('an infinite timestamp crashes the cache', cache, 'except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):', 'except (OSError, ValueError, KeyError, TypeError, RecursionError):'),
    # the source
    ('an ancient copy is shown when the server is down', source, 'old = self._read(key, STALE_LIMIT, decode)', 'old = self._read(key, 10 ** 12, decode)'),
    ('nothing is ever saved', source, 'self.cache.put(key, encode(value))', 'pass'),
    ('a saved copy is not checked when read', source, 'if ident > 0 and matches > 0 and wins <= matches:', 'if ident > 0:'),
    ('the account number is written to disk', source, 'return Player(account_id, rank, heroes)', "self.cache.put('player', [account_id]) or Player(account_id, rank, heroes)"),
    ('a fresh copy is never used', source, 'fresh = self._read(key, ttl, decode)\n            if fresh is not None:', 'fresh = None\n            if fresh is not None:'),
    # the page and the service
    ('the account is sent without being parsed', page, 'number = parse_account(self.account_field.text())', 'number = int(self.account_field.text() or 0)'),
    ('changing the choice starts a request', page, 'saved = self.service.cached_overview(*self.choice())',
     'saved = self.service.cached_overview(*self.choice()); self.service.load_overview(*self.choice(), False, lambda o: None, lambda m, c: None)'),
    ('an answer to an older question is shown', page, 'if seq == self._seq:\n            self.show_overview(overview)', 'if True:\n            self.show_overview(overview)'),
    ('a barely-above-half win rate is green', page, 'if low > 0.5:', 'if low > 0.4:'),
    ('numbers sort as text', page, 'return mine < theirs', 'return str(mine) < str(theirs)'),
    ('the hero search does nothing', page, 'heroes = [h for h in meta.heroes if needle in h.name.casefold()]', 'heroes = list(meta.heroes)'),
    ('the own-account button fills nothing', page, 'self.account_field.setText(str(own))', "self.account_field.setText('')"),
    ('a bad account is not reported', page, 'self.me_status.setText(account_problem(error.code))\n            return', 'self.me_status.setText(account_problem(error.code))\n            pass'),
    ('the difference has the wrong sign', page, 'difference = hero.win_rate - other.win_rate if other is not None else None', 'difference = other.win_rate - hero.win_rate if other is not None else None'),
    ('an older copy is not announced', page, 'if overview.meta.stale:', 'if False:'),
    ('a second load can start while one runs', service, 'if self.busy:\n            return False\n\n        def work():\n            meta = self.source.meta(', 'if False:\n            return False\n\n        def work():\n            meta = self.source.meta('),
    ('a failed comparison breaks the lookup', service, 'except RepoError:\n                meta = None', 'except ZeroDivisionError:\n                meta = None'),
    ('a failed distribution breaks the heroes', service, 'except RepoError as error:\n                problem = error.message', "except ZeroDivisionError as error:\n                problem = ''"),
    ('all time is compared with a window that does not exist', service, 'self.source.meta(window_days or COMPARE_DAYS, mode, 0)', 'self.source.meta(window_days, mode, 0)'),
    ('My stats uses the filters of the other tabs', page, 'window, mode = self.me_window.currentData(), self.me_mode.currentData()', 'window, mode, _ = self.choice()'),
    ('the window reads the wrong Steam account', window, 'return from_userdata_path(self.accounts.currentData())', 'return None'),
]

env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONIOENCODING='utf-8')
command = [str(py), '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_stats_*.py']
survivors = []
for label, path, old, new in MUTATIONS:
    if sys.argv[2:] and not any(word in label for word in sys.argv[2:]):
        continue
    original = path.read_bytes()          # bytes in, bytes out: the repository is LF and must stay LF
    text = original.decode('utf-8')
    if text.count(old) != 1:
        print('PATTERN PROBLEM (%d matches)  %s' % (text.count(old), label), flush=True)
        survivors.append(label)
        continue
    try:
        path.write_bytes(text.replace(old, new, 1).encode('utf-8'))
        result = subprocess.run(command, cwd=str(root), env=env, capture_output=True, text=True, timeout=300)
    finally:
        path.write_bytes(original)
    caught = result.returncode != 0
    print('%-9s %s' % ('CAUGHT' if caught else 'SURVIVED', label), flush=True)
    if not caught:
        survivors.append(label)
print('\nsurvivors:', survivors or 'none')
