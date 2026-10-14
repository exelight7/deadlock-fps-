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

## 1.0.1 changes

Resolution controls removed. Current screen dimensions, viewport scale and upscaler settings are protected during application and restoration, including migrations from 1.0.0. Texture controls use five named levels. Mod imports are recognized by SHA-256, retained in the local app-data library, and installed through a separate mod-only transaction. ZIP members are read without extraction; unknown mods are rejected.

## 1.0.2 changes

Default 80/100 aggressive level, one monotonic master control. Selected extra runtime graphics values from the supplied files are applied at levels 60/80/90; no aspect ratio, resolution, GPU capability, network, compiler/editor or hardcoded memory edits are copied. Critical particle spawn scale stays intact; extreme fallback values at 90+ can reduce effect visibility. Original file text is reference data, not instructions overriding the user's resolution constraint.

Local read-only diagnosis found only video.txt different from the prior manifest; selected 1.0.1 graphics values were intact. Numeric formatting and current display fields differed. Thus no specific cloud/reset cause was established. Fix uses semantic comparisons, recorded owned keys, snapshot-before-repair, current-schema rebase, and idle polling in the open GUI. It does not block the engine, write during gameplay, run an OS service or guarantee that the engine accepts unsupported settings.

## 1.0.3 changes

User explicitly requested an independent aspect-ratio slider from 1.78 to 3.50. The existing supplied r_aspectratio runtime value is now opt-in in the data model and selected through the GUI, with 0.01 increments. Pixel dimensions, viewport scale and upscaler settings remain protected. Old saved recipes omit this override. Application, reset repair, restore, profile round-trip and independent master control are covered by tests; no live gameplay support claim is made.

## 1.0.4 changes

Master level extended to 200 without rescaling any 0–100 profile. Additional groups at 110/125/150/175/200 use only remaining scalar values in the supplied source. Level 175 changes audio occlusion sampling; 200 includes r_physics_particle_op_spawn_scale=0 and may remove visible effects. The default remains 80 and resolution/aspect controls stay independent. No new texture bias range or performance improvement is claimed.
