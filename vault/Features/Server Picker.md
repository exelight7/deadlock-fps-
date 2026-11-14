---
title: Server Picker
type: feature
status: IMPLEMENTED
tags: [feature, existing]
updated: 2026-11-14
code: [deadlock_fps/servers.py, deadlock_fps/firewall.py, deadlock_fps/pages/servers.py, deadlock_fps/region_info.py]
tests: [tests/test_servers.py, tests/test_server_selection.py, tests/test_ping_ui.py]
origin: pre-existing
---

# Server Picker (pre-existing)

Measures ping per Steam relay region and blocks or allows regions through the system firewall (administrator prompt; iptables/polkit on Linux). Its `Job` (`QRunnable` with result/failure/done signals) is the pattern the Repositories page reuses to keep network work off the UI thread ([[Repository Manager]]).
