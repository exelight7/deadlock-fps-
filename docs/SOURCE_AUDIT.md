# Supplied source audit

The three outer ZIPs contain exact byte-for-byte duplicates of the extracted folders. All text configuration and nested archive text was read; compiled VPK resources and PE executables were inspected as binary data, not executed or represented as decompiled source.

| Attachment | Inspection and implementation |
| --- | --- |
| `CONFIG COPY PASTE/readme.txt` | Preserve hardware identifiers; original backup instruction implemented. DX11 note retained as context, not forced on Linux. |
| `video.txt` | 60+ supplied setting lines read; selected graphics controls mapped to real user video config. Hardware/resolution/refresh identity retained unless resolution explicitly chosen. |
| `gameinfo.gi` | All sections parsed, including rendering, scene, particles, ConVars, compiler/editor, networking, memory. Current installed file differs substantially. No wholesale replacement; graphics-only selected edits in current sections. |
| Daylock VPK | v2, 9,059,211 bytes; 7 resources: five postprocess files, sky texture/material. |
| Remove Name Tags VPK | v2, 53,876 bytes; 3 compiled HUD layout/style resources. |
| Old Healthbars VPK | v1, 50,436 bytes; 5 compiled HUD layout/script/style resources. Shares a layout with Remove Name Tags. |
| Sinner Fix VPK | v2, 1,175,954 bytes; Sinner's Sacrifice model and emissive mask texture. |
| Process Lasso | `processlassosetup64.exe`, 2,849,416 bytes. Windows executable, not a game configuration. Never executed. |
| RTSS ZIP | `RTSSSetup737.exe`, 18,078,504 bytes and Guru3D download text, 41,380 bytes. Nested archive read, executable not executed. |

VPK parser validates magic, version, tree strings, entry terminators, preload ranges and embedded data offsets. Only self-contained VPKs are accepted. A manifest with SHA-256 of every supplied file is in `source-manifest.json`.

The original gameinfo contains speculative DLL/editor/compiler entries, duplicated values, a hardcoded aspect ratio, altered latency/network defaults and very aggressive particle settings. Those are not automatically copied. Presets keep player outlines and distance-field pipeline intact, do not change GPU capability requirements, and do not apply visibility-breaking particle spawn/fallback values. Some source ConVars may be obsolete or engine-restricted; applying file values is not evidence that the current engine honors them.

The installed game and Steam userdata were read to confirm paths and current schema. Tests operate on disposable copies, not the live game. No live gameplay FPS claim is made.
