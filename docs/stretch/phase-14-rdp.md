# Phase 14: RDP and remote access

**Status:** Stretch. Beyond A+ Core 2 scope; portfolio depth toward MSP work.

## Goal

Allow Remote Desktop into `WS01` and `DC01` from another machine on the lab subnet. Limit RDP to a specific group instead of "all Administrators". Confirm with a remote session.

## Why it matters

RDP into a workstation is the most common remote-support workflow on a Windows network. Doing it through AD groups (instead of editing local Administrators on each machine) is the scalable way.

## Prerequisites

- Phase 7 complete. `WS01` is joined and reachable.
- A second machine on `VMnet1` to test from (could be the host itself, since it has an interface on `192.168.100.0/24`).

## Steps

### Part 1: Allow RDP, locked down

1. On DC01, create a group for RDP-allowed users and put yourself (or a chosen helpdesk user) in it:

   ```powershell
   New-ADGroup `
       -Name "Remote-Desktop-Users-Lab" `
       -SamAccountName "Remote-Desktop-Users-Lab" `
       -GroupCategory Security `
       -GroupScope Global `
       -Path "OU=IT,OU=Departments,DC=corp,DC=lab" `
       -Description "Lab users allowed to RDP into domain-joined hosts"

   Add-ADGroupMember -Identity "Remote-Desktop-Users-Lab" -Members jsmith
   ```

2. Create a GPO `Allow-RDP-Workstations`, link it to `OU=Workstations`. Edit it:

   `Computer Configuration > Policies > Windows Settings > Security Settings > Restricted Groups`

   Right-click > **Add Group...** > browse to `BUILTIN\Remote Desktop Users` > **OK**. In the dialog, under **Members of this group**, add `CORP\Remote-Desktop-Users-Lab`.

   This means: on every machine in `OU=Workstations`, the local built-in `Remote Desktop Users` group's membership will be **exactly** what the GPO says (nothing more, nothing less). Adding a user to `Remote-Desktop-Users-Lab` in AD propagates to every workstation at the next policy refresh.

3. Same GPO, enable the firewall rule for inbound RDP across the domain profile:

   `Computer Configuration > Policies > Windows Settings > Security Settings > Windows Defender Firewall with Advanced Security > Inbound Rules`

   Right-click > **New Rule** > Predefined > **Remote Desktop** > select both rules > **Allow the connection**.

4. Same GPO, allow RDP connections at the OS level:

   `Computer Configuration > Policies > Administrative Templates > Windows Components > Remote Desktop Services > Remote Desktop Session Host > Connections > Allow users to connect remotely by using Remote Desktop Services` = **Enabled**.

   And: `... > Security > Require user authentication for remote connections by using Network Level Authentication` = **Enabled**. (NLA prevents pre-auth attacks; should always be on.)

5. From WS01:

   ```powershell
   gpupdate /force
   ```

   Wait a minute or reboot.

### Part 2: Connect

6. From the host machine (or another lab VM), open `mstsc`. Server: `WS01.corp.lab` or `192.168.100.20`. Username: `corp\jsmith`. Password: lab password.

7. You should land on a fresh `jsmith` session on `WS01`. `whoami` returns `CORP\jsmith`, `query session` on the box shows two sessions if someone is logged in at the console.

## Verify

From WS01:

```powershell
# Confirm local membership now reflects the AD group via Restricted Groups
net localgroup "Remote Desktop Users"

# Confirm the firewall rule is on
Get-NetFirewallRule -DisplayGroup "Remote Desktop" |
    Select-Object DisplayName, Enabled, Profile

# Confirm RDP is allowed at the system level
(Get-ItemProperty "HKLM:\System\CurrentControlSet\Control\Terminal Server").fDenyTSConnections
```

!!! success "Pass criteria"
    - `net localgroup "Remote Desktop Users"` lists `CORP\Remote-Desktop-Users-Lab`.
    - The RDP firewall rule is `Enabled = True` on the Domain profile.
    - `fDenyTSConnections` = `0`.
    - A remote `mstsc` session from the host as `corp\jsmith` connects successfully.

## Snapshot

No new snapshot. The change is GPO-driven; rollback is unlinking the GPO.

## Gotchas

!!! danger "Restricted Groups is destructive"
    `Members of this group` REPLACES the local group's membership wholesale. Anyone currently in `Remote Desktop Users` on the local machine who is not in the AD group will be removed on the next refresh. Use the **less destructive** "Members" semantics deliberately, and consider the alternate **Group Policy Preferences > Local Users and Groups > Update Group** path if you want to add without removing.

!!! warning "RDP is fine on the lab subnet, never expose it to the internet directly"
    Plain RDP across the internet is one of the top three ways networks get ransomware. In real environments, RDP sits behind a VPN, a Remote Desktop Gateway, or a zero-trust broker.

!!! warning "NLA on, every time"
    Without NLA, the server has to render the logon screen before authenticating, which means pre-auth code is doing work for an anonymous attacker. Enable NLA and require it.

!!! warning "RDP into a DC is a separate decision"
    By default, only the local `Administrators` group can RDP to a domain controller, and that group on a DC is `BUILTIN\Administrators`, which already includes Domain Admins. Adding a non-admin to `Remote Desktop Users` on a DC requires also granting them the "Allow log on through Remote Desktop Services" user right, which the lab does not need.
