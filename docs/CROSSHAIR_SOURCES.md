# Crosshair catalog and preview references

Checked 2026-10-15. These are offline numerical snapshots **attributed to Deadlock Labs**, not independent verification of a player's current preferences. The gallery includes all nine entries in that site's pro/streamer category when checked; it is not a claim to contain every professional player in the world. No player photos, website code, or remote image assets are bundled.

| Name | Source's settings date | Published values |
| --- | --- | --- |
| [Hydration](https://deadlocklabs.gg/crosshairs/pro/hydration/) | 2026-03 | Full displayed numeric settings |
| [Dimov](https://deadlocklabs.gg/crosshairs/pro/dimov/) | 2026-04 | Full displayed numeric settings |
| [Vegas](https://deadlocklabs.gg/crosshairs/pro/vegas/) | 2026-02 | Full displayed numeric settings |
| [Lefaa](https://deadlocklabs.gg/crosshairs/pro/lefaa/) | 2025-02 | Full displayed numeric settings |
| [Sharyk](https://deadlocklabs.gg/crosshairs/pro/sharyk/) | 2024-10 | Full displayed numeric settings |
| [Dew](https://deadlocklabs.gg/crosshairs/pro/dew/) | 2026-06 | Only gap, width and length; other values are explicitly marked defaults |
| [crayon](https://deadlocklabs.gg/crosshairs/pro/crayon/) | 2025-06 | Only gap, width and length; other values are explicitly marked defaults |
| [shroud](https://deadlocklabs.gg/crosshairs/pro/shroud/) | 2024-09 | Full displayed numeric settings |
| [MikaelS](https://deadlocklabs.gg/crosshairs/pro/mikaels/) | 2025-03 | Full displayed numeric settings |

Themed and collapse flags use the Toolbox model's explicit false defaults; they were not exposed in the source's settings tables. Motion/static values match the source tables. The original native DL code strings are not bundled or advertised as supported imports. The application writes its own validated native configuration, after review and backup.

Preview geometry was compared to the user's supplied gameplay images and the **observable SVG geometry** in [the current Deadlock Labs editor](https://deadlocklabs.gg/crosshairs/create/): static gap 0 / length 6 puts the inner edge at 8; adding preview spread 8 puts it at 16. No website rendering code was copied. This supports the base-gap correction, not a guarantee of exact behavior in every native weapon/hero state.

Native dimension types were checked against the installed game and the extracted [CustomCrosshairSettings_t schema](https://github.com/SteamTracking/GameTracking-Deadlock/blob/master/DumpSource2/schemas/client/CustomCrosshairSettings_t.h). The schema documents int32 pip and dot dimensions. Game configuration writes, restore and conflict handling remain covered by temporary-file tests.

## Studio collection (2.2.2)

PRO Crosshairs contains 50 built-in choices: the 9 attributed player snapshots above, 5 existing Toolbox presets, and 36 new original Studio designs. Studio designs are clearly labeled **STUDIO**, are fully editable, and carry no player attribution. The gallery supports name search, source-group filters, and Cross/Dot/Ring/Hybrid filters. Existing saved profiles remain separate and retain their user-chosen names.

All 50 built-in designs have distinct native settings and are validated and share-code roundtrip tested. Rendering remains event-driven; thumbnails are cached within the gallery and released after it closes. No network access is needed to browse.
