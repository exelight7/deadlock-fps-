# Mod manager guide (Toolbox 4.0)

How to find, install, update and remove mods from repositories. The older guide for the four built-in reference mods is [MOD_INSTALL.md](MOD_INSTALL.md) (Arabic); both keep working side by side.

## 1. Link your game
Open **Home** and let Toolbox find Deadlock, or pick the folder yourself. Mods are installed into that folder's `game/citadel/addons`. Close the game before installing, updating, disabling or removing anything.

## 2. Add a repository (Repositories)
Paste an address and press **Add and load**:

| You paste | Toolbox treats it as |
|---|---|
| `https://github.com/owner/project` | a GitHub project |
| `https://gitlab.com/group/project` | a GitLab project (a self-hosted GitLab: choose *Self-hosted GitLab*) |
| `https://example.org/mods/index.json` or a folder address | a custom HTTPS repository |

Or press **Import file…** for a repository index you were given, or for a shared list of addresses. **Export list…** saves yours.

Each row says how well Toolbox understands the repository:

* **Native** — the author published an index in the open format ([specification](REPOSITORY_SPEC.md)).
* **Translated** — no index, but `.vpk` files are attached to releases. The catalogue is built from that, with no description, no compatibility information and often no checksum, and the file is inspected before install.
* **Needs manual mapping** — only ZIP archives are published. Toolbox will not guess what is inside; someone has to write a mapping index.
* **Unsupported** — nothing usable; the reason is shown.

The **Trust** column is what the Toolbox project knows about the source. Every repository you add yourself is **UNVERIFIED**: nobody has reviewed it.

## 3. Install (Mod Hub)
Search, pick a mod and a version, press **Install**. Toolbox then:

1. downloads the file and checks it against the SHA-256 the repository published;
2. inspects it (the archive, and the VPK inside);
3. shows a **preview**: where it came from and its trust label, the files that will be installed and under which names, overlaps with other mods, and every warning;
4. installs only after you confirm (UNVERIFIED sources and missing checksums also need an explicit acknowledgement);
5. re-checks every installed file and reports success only then.

If anything fails, or the app is closed unexpectedly, the game folder is put back exactly as it was.

## 4. Installed Mods
* **Check for updates** refreshes your repositories and compares versions. **Update all** prepares every update and asks once.
* **Restore previous version** swaps back to the last version; the one you leave is kept, so you can switch again. Up to three earlier versions are kept.
* The **On** box disables a mod by moving its files out of the addons folder, the only place the game loads them from. Tick it again to bring them back.
* **Remove** moves the files to Toolbox's recovery folder (the last five removals are kept).
* **Files…** and **History…** show exactly what is on disk and what happened.

## 5. Compatibility and troubleshooting
* **Steam restored `gameinfo.gi`** (after an update or *Verify integrity*): mods stop loading. Compatibility shows *inactive*; press **Repair**.
* **Overlaps:** when two mods provide the same file, the lower `pakNN` number wins. That is how the game loads them; Toolbox reports it and does not hide it.
* **A mod was refused:** the preview or the message says why (checksum mismatch, unsafe archive, multi-file VPK, missing dependency, declared conflict).
* **Files not installed by Toolbox** in the addons folder are listed and never touched.

## Where things are stored
Inside the game folder, `.deadlock-fps-studio/mods/`: `installed.json` (what is installed), `backups/`, `trash/`, `disabled/`, and a short-lived `staging/`. The repository list and cached catalogues are in Toolbox's app-data folder under `repositories/`.
