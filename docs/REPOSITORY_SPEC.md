# Deadlock Mod Repository Specification — version 1.0

How to publish a mod repository that Deadlock Toolbox can add, browse and (once the installation engine ships) install from.
This document describes what the code in `deadlock_fps/repos/spec.py` actually enforces; the code is the source of truth.

**Status of this document:** the catalogue side (everything below) is implemented and tested. Installing from a repository is **not implemented yet**; today Toolbox can add, sync, classify, search and show repositories, not install from them.

## 1. Hosting

A repository is one JSON file, the **index**. Host it anywhere that serves HTTPS:

| You publish it as… | Toolbox calls it | How the user adds it |
|---|---|---|
| `deadlock-repo.json` in the root of a GitHub repository's default branch | `github` provider, **native** | paste the repository URL |
| `deadlock-repo.json` attached to a GitHub Release | `github` provider, **native** | paste the repository URL |
| `deadlock-repo.json` in the root of a GitLab project's default branch | `gitlab` provider, **native** | paste the project URL |
| any file on any HTTPS server, or a folder URL that contains `deadlock-repo.json` | `https` provider, **native** | paste the file or folder URL |
| a file you give to users | local import, **native** | *Import file…* |

Requirements for every address (the index itself, packages, screenshots, homepages):

* `https://` only, no embedded credentials, default port (443);
* a public host name. `localhost`, single-label names, `.local`/`.lan`/`.internal`, and private, loopback or link-local IP addresses are refused, and so is any name that *resolves* to one;
* at most 2048 characters, no spaces or control characters.

The index is limited to **8 MiB** and **5000 mods**; a mod to **200 versions**. Servers should send `ETag`; Toolbox then asks "has it changed?" instead of downloading the index again.

## 2. The index

```json
{
  "schema": "deadlock-mod-repository",
  "schema_version": "1.0",
  "repository": { "id": "example-mods", "name": "Example Mods", "description": "…", "homepage": "https://example.org", "maintainer": "Mira" },
  "mods": [ { "id": "crimson-skin", "name": "Crimson Skin", "versions": [ … ] } ]
}
```

A complete, validated example is in [`docs/repository-example/deadlock-repo.json`](repository-example/deadlock-repo.json).

### Top level

| Field | Required | Notes |
|---|---|---|
| `schema` | yes | exactly `deadlock-mod-repository` |
| `schema_version` | yes | `"MAJOR.MINOR"`. Toolbox reads every `1.x`; another major is refused with a clear message |
| `repository.id` | yes | your own identifier, ≤ 64 characters. Not used for trust or identity (see §6) |
| `repository.name` | yes | ≤ 120 characters |
| `repository.description` | no | ≤ 1000 |
| `repository.homepage` | no | https URL |
| `repository.maintainer` | no | ≤ 120 |
| `repository.updated` | no | ISO 8601 date |
| `mods` | yes | list |

### Mod

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `[a-z0-9][a-z0-9._-]*[a-z0-9]`, 2–64 characters. **Never change it**: dependencies and installed-mod tracking use it |
| `name` | yes | ≤ 120 |
| `author` | yes | ≤ 120 |
| `summary` | no | one line, ≤ 300 |
| `description` | no | ≤ 16 000, plain text (see §7) |
| `license` | no | SPDX identifier or a short name |
| `categories`, `tags` | no | lists of ≤ 32 words of ≤ 40 characters; stored lower-case |
| `homepage`, `source_url` | no | https URLs. `source_url` is where the original work lives |
| `screenshots` | no | up to 12 https URLs |
| `published` | no | ISO 8601 |
| `versions` | yes | non-empty list, see below |

### Version

| Field | Required | Notes |
|---|---|---|
| `version` | yes | 1–4 numeric parts with an optional SemVer pre-release: `1.4`, `2.0.1`, `1.0.0-beta.2`. `1.4` equals `1.4.0`. Duplicates within a mod are ignored (first wins) |
| `package` | yes | see below |
| `install` | yes | see below |
| `published` | no | ISO 8601 |
| `changelog` | no | ≤ 16 000, plain text |
| `game.min_build`, `game.max_build`, `game.tested_build` | no | Steam build ids (integers) of Deadlock. Outside `min`/`max` → *incompatible*; nothing declared → *unknown*; a lower bound without an upper bound is only *untested* on newer builds |
| `dependencies` | no | `[{"id": "other-mod", "range": ">=1.2 <2"}]` |
| `conflicts` | no | `[{"id": "other-mod", "range": "*", "reason": "…"}]` |
| `prerelease` | no | `true`, or implied by a pre-release version number |
| `yanked` | no | `true` withdraws a version: it is shown in history but never offered |

**Ranges** are space-separated comparators that must all hold: `>=`, `<=`, `>`, `<`, `=`, `!=`, or `*`.

### Package

| Field | Required | Notes |
|---|---|---|
| `format` | yes | `vpk` or `zip`. Anything else makes that version *unsupported* (shown, not installable) |
| `url` | yes | https download address |
| `size` | yes | bytes, 1 – 2 GiB. Used to reject oversized or truncated downloads |
| `sha256` | recommended | 64 hex characters. **Without it Toolbox can only warn, not verify** |
| `mirrors` | no | up to 8 alternate https URLs for the same bytes |

### Install

```json
"install": { "type": "vpk", "files": [ { "source": "pak/crimson.vpk" } ] }
```

Only `type: "vpk"` exists in 1.0: the listed Valve package files are copied into the game's add-on folder. Toolbox chooses the destination and the load-order slot; you do not. Rules:

* `package.format = "vpk"` installs itself; `files` is empty or a single `{"source": ""}`.
* `package.format = "zip"` must list every `.vpk` to install. `source` is a relative path inside the archive: letters, digits, space and `. _ ( ) + -`, no leading dot, no `..`, no drive letters, no backslashes, no streams.
* **Only `.vpk` files can be installed.** Executables, scripts, DLLs and everything else are never copied into the game, whatever the archive contains.

A version that is well-formed but names a format or install type this build does not know is kept and marked unsupported with the reason, so users learn they need a newer Toolbox instead of the mod silently vanishing.

## 3. What Toolbox does with what you publish

1. Validates the index against everything above. **One bad mod or version is skipped with a warning; the rest of the index still works.** Structural problems (wrong schema, not JSON, too large) make the whole repository *unsupported* with the reason shown.
2. Ignores fields it does not know, so later 1.x versions can add fields safely.
3. Shows the repository's **compatibility class**:

| Class | Meaning |
|---|---|
| **Native** | you published this specification |
| **Translated** | no index, but a provider integration derived a catalogue from release metadata. Only `.vpk` release assets qualify. Descriptions are generic, game compatibility is unknown, and a hash is present only when the host reports one |
| **Needs manual mapping** | recognised, but only archives (`.zip`) are published. An archive can contain anything, so Toolbox never guesses; someone must write a mapping index (an ordinary index whose `package.url` points at the release asset) and import it |
| **Unsupported** | nothing usable; the reason is shown |

Toolbox never silently treats an arbitrary file as an installable mod.

## 4. Sharing a set of repositories

```json
{
  "schema": "deadlock-mod-repository-list",
  "schema_version": "1.0",
  "repositories": [ { "url": "https://github.com/owner/repo", "name": "Owner's mods" }, { "url": "https://mods.example.org/", "provider": "https" } ]
}
```

Importing a list **only registers the addresses**; nothing is fetched until the user refreshes. `provider` may be `gitlab` for a self-hosted GitLab or `https`. Every entry is added as UNVERIFIED.

## 5. Self-hosted GitLab

`gitlab.com` projects are recognised automatically. For another server the user chooses *Self-hosted GitLab* when adding it; Toolbox then talks to `/api/v4` on that host.

## 6. Trust

Trust labels (`OFFICIAL`, `VERIFIED`, `COMMUNITY`, `UNVERIFIED`) are **not** part of the index. A repository cannot declare itself verified, and hosting on a well-known service confers nothing. Labels come only from a registry shipped inside Toolbox and keyed by the repository's canonical address (`github:owner/repo`, `gitlab:host/group/project`, `https:host/path`). Every repository a user adds by hand is `UNVERIFIED`. To request a review, open an issue on the Toolbox repository.

## 7. Authoring advice

* Treat every text field as **plain text**. Toolbox shows it verbatim and never renders HTML or Markdown from a repository.
* Always publish `size` **and** `sha256`; users see a warning for packages without a hash.
* Keep a version's file immutable once published. Fix problems by publishing a new version and `yanked`-ing the broken one.
* State `game.tested_build` honestly. *Unknown* is better than a false *compatible*.
* Never change a mod's `id`.

## 8. Versioning of this specification

* Minor versions (`1.1`, `1.2`) only add optional fields. Older Toolbox builds ignore them.
* A new major version changes meaning; older builds refuse it with an explicit message.
* The set of `package.format` and `install.type` values grows in minor versions; builds that do not know a value mark that version unsupported rather than failing.

## 9. Known limits (today)

* No installation from repositories yet (Milestone 4).
* Only the first 30 releases of a GitHub or GitLab project are read.
* System HTTP proxies are not used; users behind a mandatory proxy cannot sync.
* Package signatures are not supported; integrity is `sha256` from the index, which protects against corruption and a swapped download, not against a malicious index. That is what trust labels are for.
