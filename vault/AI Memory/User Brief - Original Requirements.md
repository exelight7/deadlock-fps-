---
title: User Brief - Original Requirements
type: guide
tags: [ai-memory, requirements]
updated: 2026-11-14
---

# The user's messages, verbatim

Copied by script from the session transcript, so not one character is paraphrased. These are the requirements. When a decision is unclear, this note beats any summary, including [[00 Start Here]] and [[Session History]].

The user writes Arabic (a Gulf-style dialect) and English. Message 1 is English; the rest are Arabic.

## Message 1

*The original brief. Everything else grew from this.*

~~~~text
Deadlock Mod Manager — Full Platform Evolution
You are the principal software architect, senior engineer, product designer, and technical lead.
Existing Project: https://github.com/exelight7/deadlock-fps-
Your mission is to evolve this existing project into a powerful, polished, extensible Deadlock Mod Manager.
This is not a simple mod downloader.
I want a complete desktop mod management platform where users can discover, import, download, install, update, organize, inspect, and remove mods from multiple independent repositories.
The platform must be able to grow beyond its original built-in mod collection.
Do not rebuild everything blindly. Audit the existing codebase, preserve working functionality, and evolve it intelligently.
1. THE MOST IMPORTANT REQUIREMENT: MULTIPLE EXTERNAL REPOSITORIES
Users must be able to download mods from repositories other than the project's own repository.
Do not restrict users to a single official repository.
I want users to be able to add repositories themselves.

Supported repository sources
Design an extensible system supporting:

* GitHub repositories.
* GitHub Releases.
* GitLab repositories and releases.
* Custom HTTPS repository URLs.
* Independent mod-hosting servers.
* Community-maintained repositories.
* Future providers without changing the core application.

The application should not depend on one hosting provider.
Repository Manager
Build a dedicated Repository Manager where users can:

* Add a repository using its URL.
* Import repository configuration.
* Remove repositories.
* Enable or disable repositories.
* Refresh repository data.
* View repository status.
* View available mods.
* View repository metadata.
* See the last synchronization time.
* See errors when a repository is unavailable.
* Update repository indexes.
* Search across all enabled repositories.

Users must not need to visit external websites just to download a mod.
They should be able to perform the entire workflow inside the application.
Important compatibility rule
Do not assume every GitHub repository automatically has a compatible mod manifest.
Implement a clear repository compatibility system:

1. Native repositories using the application's manifest specification.
2. Supported provider integrations that can translate known release metadata.
3. External repositories requiring a manual import or mapping process.
4. Unsupported repositories that clearly explain why they cannot be used.

Never silently interpret arbitrary files as installable mods.
Support both repository indexes and individual mod imports where appropriate.
2. BUILD A REAL MOD MANAGEMENT EXPERIENCE
The application must provide a complete mod lifecycle.
Mod Hub
Create a discovery interface with:

* Mod name.
* Description.
* Author.
* Repository.
* Version.
* Last updated.
* Download size.
* Screenshots.
* Changelog.
* License.
* Supported Deadlock versions.
* Compatibility status.
* Trust status.

Features:

* Global search.
* Categories.
* Sorting.
* Filters.
* Mod details.
* Install.
* Update.
* Uninstall.
* Update all.
* Installed status.
* Version history.

Installed Mods
Create a dedicated page showing all installed mods.
For every mod, show:

* Installed version.
* Available version.
* Source repository.
* Installation location.
* Enabled/disabled status.
* Compatibility.
* Detected conflicts.
* Update availability.

Allow users to:

* Enable and disable mods where technically supported.
* Update individual mods.
* Update all compatible mods.
* Remove mods.
* Restore original files.
* Inspect installed files.
* Open the source repository.
* View installation history.

Do not pretend a mod can be disabled independently if the game's file format or installation method does not support that behavior.
Manual Mod Installation
Users must also be able to import mods manually.
Support the formats and structures that the actual Deadlock mod ecosystem uses, after investigating them.
Potential import sources:

* ZIP archives.
* VPK files.
* Mod folders.
* Local files.
* Downloaded packages.

Do not assume every format is directly installable. Inspect and validate the actual content.
3. MOD INSTALLATION ENGINE
Build a reliable installation system.
Required capabilities:

* Detect Deadlock installation directories.
* Support custom game locations.
* Validate mod packages.
* Preview files before installation.
* Detect duplicate files.
* Detect potential conflicts.
* Track installed files.
* Backup originals.
* Safely replace files.
* Restore previous versions.
* Roll back failed installations.
* Track installation history.

Use a staged installation process:
`Download → Verify → Inspect → Stage → Backup → Install → Verify → Commit`
If any step fails, recover safely.
Never overwrite files without a recovery strategy.
Make the installation engine independent from the UI so it can be tested properly.
4. REPOSITORY AND MOD TRUST SYSTEM
External repositories are welcome, but their content must not all be treated equally.
Use clear trust labels:

* OFFICIAL
* VERIFIED
* COMMUNITY
* UNVERIFIED

These labels must describe actual review status, not hosting provider reputation.
A GitHub repository is not automatically trusted.
Display the source and trust status clearly before installation.
Security requirements:

* HTTPS downloads.
* SHA-256 verification when a trusted hash is available.
* File-size limits.
* Archive inspection.
* ZIP path traversal prevention.
* Symlink protection.
* ZIP bomb protection.
* Installation path restrictions.
* Safe temporary staging.
* Backup and rollback.
* No automatic execution of downloaded EXE or scripts.
* No hidden background installation.
* Clear warnings for unverified content.

Never weaken security to make repository compatibility easier.
5. UNIVERSAL REPOSITORY ARCHITECTURE
Design a common repository abstraction.
The application should communicate with different repository providers through a consistent interface.
Define:

* Repository Provider.
* Repository Index.
* Mod Manifest.
* Mod Package.
* Release.
* Version.
* Compatibility Metadata.
* Download Source.
* Trust Metadata.

Use a versioned manifest specification.
A mod manifest should support fields such as:

* Unique ID.
* Name.
* Description.
* Author.
* Version.
* Game compatibility.
* Package format.
* Download URL.
* File size.
* SHA-256.
* Installation instructions.
* Target paths.
* Dependencies.
* Conflicts.
* License.
* Changelog.
* Screenshots.
* Original source URL.
* Published date.

Support future manifest versions without breaking older repositories.
Do not require every external repository to use the same hosting platform.
Document the specification so independent developers can create compatible repositories.
6. OBSIDIAN — THE PROJECT'S SECOND BRAIN
Obsidian is mandatory for project knowledge management.
Locate an existing suitable Obsidian vault. If none exists, create a dedicated project vault without modifying unrelated personal notes.
Use Obsidian to document the actual project continuously.
Maintain:

* Architecture.
* Codebase structure.
* Feature specifications.
* Repository specifications.
* Mod lifecycle.
* Security model.
* Design system.
* Technical decisions.
* Dependencies.
* Bugs.
* Testing.
* Roadmap.
* Implementation history.

Use Markdown, YAML frontmatter, tags, and `[[Wikilinks]]`.
Maintain accurate statuses:
`PROPOSED`
`IN PROGRESS`
`IMPLEMENTED`
`VERIFIED`
Update documentation whenever significant code or design changes occur.
Never document a feature as implemented if it is only planned.
The codebase is the source of truth for actual implementation.
Obsidian is the central knowledge map explaining the project.
7. INTERACTIVE KNOWLEDGE GRAPH INSIDE THE APPLICATION
Build a real, interactive Graph View inside Deadlock Mod Manager.
This must visualize actual project and mod relationships.
Graph nodes should include:

* Modules.
* Features.
* Repositories.
* Mods.
* Versions.
* Authors.
* Dependencies.
* Conflicts.
* Game versions.
* Tasks.
* Technical decisions.
* Documentation.

Relationships should include:

* Repository publishes Mod.
* Mod has Version.
* Mod depends on Mod.
* Mod conflicts with Mod.
* Mod supports Game Version.
* Module contains Feature.
* Feature is implemented by Task.
* Documentation describes Feature.
* Decision affects Module.

Interactions:

* Pan.
* Zoom.
* Search.
* Filter.
* Node selection.
* Relationship highlighting.
* Focus mode.
* Expand and collapse groups.
* Node details.
* Navigation to relevant application pages.
* Navigation to Obsidian documentation.

The graph must use real data.
Do not fill it with fake demo relationships.
Use Obsidian Wikilinks so its native Graph View also reflects the knowledge structure.
Make the in-app graph visually impressive, readable, responsive, and useful.
8. UI AND PRODUCT DESIGN
I want this to look and feel like a premium modern desktop application.
Audit the existing interface before making changes.
Create a consistent design system.
Main navigation:

* Dashboard.
* Mod Hub.
* Repositories.
* Installed Mods.
* Collections.
* Compatibility.
* Downloads.
* Knowledge Graph.
* Backup & Restore.
* Settings.

Important UX requirements:

* Excellent typography.
* Clean spacing.
* Strong visual hierarchy.
* Consistent icons.
* Smooth transitions.
* High-quality cards.
* Clear installation progress.
* Useful notifications.
* Beautiful empty states.
* Proper error handling.
* Dark and light themes if supported by the existing architecture.
* Keyboard navigation.
* Responsive layouts.

Avoid generic dashboard templates.
Do not overuse glass effects, gradients, or excessive animations.
The application must feel like one coherent product.
9. ENGINEERING AND IMPLEMENTATION RULES
Before changing code:

1. Inspect the complete existing repository.
2. Understand its architecture and framework.
3. Identify existing features.
4. Understand the current mod installation system.
5. Inspect the existing inspector and safety mechanisms.
6. Identify reusable components.
7. Map dependencies.
8. Identify technical debt.
9. Document findings in Obsidian.

Preserve working features.
Do not introduce unnecessary frameworks or dependencies.
Keep repository providers independent from the installation engine.
Keep the UI independent from business logic.
Write maintainable, testable code.
Do not create fake implementations.
Do not leave important buttons nonfunctional.
Do not claim successful installation without verification.
Do not modify unrelated user files.
Do not perform destructive operations without explicit authorization.
10. IMPLEMENTATION ROADMAP
Work in controlled milestones.
Milestone 1 — Audit and Second Brain
Understand the current project, locate Obsidian, document the existing architecture, and create the roadmap.
Milestone 2 — Repository Engine
Implement multiple repository sources, provider abstraction, manifest validation, repository synchronization, and error handling.
Milestone 3 — Mod Hub
Build discovery, global search, filtering, mod details, and source information.
Milestone 4 — Mod Installation Engine
Implement download, inspection, staging, backup, installation, rollback, and uninstall.
Milestone 5 — Installed Mods and Updates
Build installed mod management, version tracking, compatibility, and update workflows.
Milestone 6 — Knowledge Graph
Build the interactive graph and connect it to actual project data and Obsidian.
Milestone 7 — UI Refinement
Polish the entire application and make the experience consistent.
Milestone 8 — Testing and Verification
Test repository providers, package validation, installation, rollback, security, UI, and graph consistency.
Update Obsidian at every milestone.
11. HOW TO PRIORITIZE
The priority is:

1. A reliable multi-repository system.
2. Safe and correct mod installation.
3. Excellent mod discovery and management.
4. A polished desktop experience.
5. The interactive knowledge graph.
6. Long-term extensibility.

Do not spend excessive time polishing a screen while the underlying feature is incomplete.
Build real functionality first, then refine its presentation.
Make sensible technical decisions autonomously. Do not interrupt development for ordinary implementation choices.
If a major limitation or destructive risk exists, document it and explain it.
FINAL MISSION
Turn this existing project into a serious Deadlock Mod Manager that supports multiple independent repositories.
I want users to be able to add a repository URL, browse its available mods, download them, install them, manage versions, and remove them — all inside the application.
I also want Obsidian to preserve the complete project knowledge and an excellent interactive Graph View to make the system understandable.
Start by inspecting the actual codebase.
Create the Obsidian knowledge base.
Then implement the first meaningful milestone.
Do not stop at planning. Make measurable progress in the real project, verify what you build, and keep the documentation synchronized with the code.
Build a real mod management platform, not just a mod catalog.
~~~~
## Message 2

*Arabic: "repeat what you said, speak to me in Arabic". From here on, reply in Arabic.*

~~~~text
عيد سوالك تكلم معي عربي
~~~~
## Message 3

*Arabic: "continue the work; this version is an upgrade to 4.0.0, make it something big".*

~~~~text
كمل شغل النسخه هي تطوير الى 4.0.0 تكون شي كبير
~~~~
## Message 4

*Arabic: "no, run the program so I can see".*

~~~~text
لا شغل لي البرنامج بشوف
~~~~
## Message 5

*Arabic: "I did not like it currently. I will open a new chat. I want you now to move all the records you know about the project into the Obsidian vault, treating the project as complete information and memory for the AI so it never forgets anything, because I will start a new chat". **The reason for the dislike was not stated.***

~~~~text
ما اعجبني حاليا بفتح دردرشه جديد ابيك الان تنفل كل سجلات الي تعرف في مشروع وتنقله الى vault في برنامج obsidian كامل بي اعتيباره المشروع كامل معلومات في وذكاره لي ذكاء الاصطناعي لي كي لاينسى شي للابد  لي بسوي دردشه جديده
~~~~

## How the first brief maps to what exists

| Brief section | Where it lives |
|---|---|
| 1 Multiple external repositories (providers, Repository Manager, compatibility classes) | [[Repository Manager]], [[Repository Providers]], [[Manifest Specification]] |
| 2 Real mod management (Mod Hub, Installed Mods, manual import) | [[Mod Hub]], [[Installed Mods]]. Manual import of ZIP/VPK/folders for the four reference mods is [[Existing Mod Library]]; **manual import of arbitrary local mod files into the new installer does not exist yet** ([[Open Items and Next Steps]]) |
| 3 Installation engine | [[Installation Engine]], [[Mod Lifecycle]] |
| 4 Trust system and security | [[Trust System]], [[Security Model]] |
| 5 Universal repository architecture and versioned manifest | [[Manifest Specification]], [[Repository Specification]] |
| 6 Obsidian second brain | this vault: [[Vault Guide]], [[Status Legend]] |
| 7 In-app knowledge graph | [[Knowledge Graph]] |
| 8 UI and product design (named navigation: Dashboard, Mod Hub, Repositories, Installed Mods, Collections, Compatibility, Downloads, Knowledge Graph, Backup & Restore, Settings) | [[Design System]]; Collections is **not built** ([[Collections]]) |
| 9 Engineering rules | [[Architecture Overview]], [[Technical Debt]] |
| 10 Milestones 1-8 | [[Roadmap]] |
| 11 Priorities | multi-repository system, then safe installation, then discovery, then polish, then graph |
