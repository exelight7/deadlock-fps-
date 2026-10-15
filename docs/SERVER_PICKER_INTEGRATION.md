# Deadlock Toolbox — server integration

Deadlock Toolbox implements the server selection workflow in the same native Qt window as graphics and mods. Release 2.1.3 includes the integration and selection fixes.

## Inspected inputs

The supplied `/home/kaito/deadlock severs/ServerPickerX-Linux/` contains a Linux .NET executable, PDB, native drawing libraries and launch script, not source. Its embedded repository identifier points to [ServerPickerX](https://github.com/FN-FAL113/server-picker-x). The upstream source was inspected in a temporary reference checkout to understand feature behavior and its GPL-3.0 license. No upstream code, executable, libraries, flags, fonts or artwork are embedded in Toolbox. The native Python/Qt implementation is independent and retains the project's existing MIT source license. ServerPickerX's licensing and credits remain its own.

## Integrated features

- Native Arabic server page in the same window, alongside existing graphics, aspect-ratio, mods and restore pages.
- Deadlock-only Steam SDR catalog from the public Valve endpoint, manual refresh and offline snapshot/cache.
- Relay region search, three-sample ICMP latency/loss diagnostics, saved selections.
- Block selected, unblock selected, keep selected available, clear Toolbox-owned blocks.
- Preview before apply and one short-lived privileged helper; the GUI stays unprivileged.
- Linux: UDP destination filtering in the dedicated `DLTB_OUT` chain, installed via `iptables-restore --noflush`. No global flush or policy changes. Failed replacements restore the prior owned rules.
- Windows: deterministic `DeadlockToolbox_SDR_` rule names with UDP/IP/port scope via netsh. UAC helper, add-first/rollback handling, prefix-scoped removal.
- Shared relay endpoints used by an available region are excluded from deny plans.
- Existing `.deadlock-fps-studio` backups and the old mod library remain usable after rebranding.

The selector steers available relay routes; it cannot guarantee a matchmaking region. Rules may affect other Steam games sharing the relay endpoints. Linux rules are not installed as a boot service; reapply after restart. The table shows last saved selection, not a privileged inspection of actual kernel/firewall state. Previous ServerPickerX rules are not imported or removed automatically.

## Validation limits

Unit tests cover parsing, public IP/port validation, injection rejection, region selection/presets, shared endpoints, scoped Linux/Windows commands and rollback behavior. All firewall calls in tests use mocks. Real Valve catalog fetching returned 32 regions; a three-sample Dubai ICMP probe returned 44.6 ms average and 0% ICMP loss at test time. A local portable Linux GUI startup is checked separately. No live rules or match connections were changed on the user’s machine. CI builds Windows and Linux, starts each portable executable, and checks real netsh block/unblock/clear on its disposable Windows runner. This does not validate matchmaking behavior or the interactive UAC/polkit dialogs on every system.

## References

- [Steam SDR](https://partner.steamgames.com/doc/features/steam_datagram_relay)
- [iptables manual](https://man7.org/linux/man-pages/man8/iptables.8.html)
- [Windows firewall rule documentation](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule)
- [ServerPickerX upstream and license](https://github.com/FN-FAL113/server-picker-x)

## 2.0.1 local — ping and selection clarity

Automatic on-show measurement with live per-region progress, explicit unmeasured/measuring/no-reply/tool-error states, up to three relay candidates per region, numerical latency sorting and precise error reasons. Tool failures have unknown loss instead of fabricated 100% loss. Region latency is the average of up to three ICMP replies from the first responsive candidate, not actual match RTT or an average across every relay. A custom Qt delegate paints a real high-contrast checkmark and handles whole-cell clicks; selection count explains that checking a row does not apply a firewall rule.

## 2.1.3 release validation

Local unit/interface tests include actual delegate painting, selection by row/checkbox/keyboard, hidden selections, live ping sorting, and scoped firewall command plans. `scripts/smoke_windows_firewall.py` checks netsh-created rules by DisplayName and verifies that clear preserves a sentinel outside the owned hash namespace. `scripts/smoke_desktop.py` verifies executable startup and packaged assets.
