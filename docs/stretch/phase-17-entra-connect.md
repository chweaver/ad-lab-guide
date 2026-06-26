# Phase 17: Entra Connect hybrid identity

**Status:** Stretch. The hybrid-identity bridge from the AD lab to the AI Security Lab series.

## Goal

Sync the on-prem `corp.lab` users into a **Microsoft Entra ID** tenant using **Microsoft Entra Connect**, so the same accounts exist on-prem and in the cloud. End state: the Departments users (jsmith, mtate, and the rest) appear in Entra ID as directory-synced objects, with their passwords usable in the cloud through password hash sync. This is the hybrid-identity model every Microsoft 365 customer runs, and it is the bridge from this AD lab into the AI Security Lab series.

## Why it matters

Hybrid identity is the backbone of modern MSP work: on-prem AD stays the source of authority, and the cloud trusts it. This phase teaches the things that actually break real syncs: the non-routable-domain UPN problem, sync scoping by OU, and the difference between password hash sync, pass-through auth, and federation. It also sets up AI Security Lab Phase 4, where an Azure AI service is locked down with these same Entra identities.

## Prerequisites

- A healthy `corp.lab` domain (Phases 1 through 8). A second DC (Phase 16) is recommended, not required.
- A **Microsoft Entra tenant**. Entra ID Free (included with a free Azure account) is enough for directory sync. [VERIFY] the current free path: a free Azure account creates a default tenant; the Microsoft 365 Developer Program sandbox now needs an eligible subscription, so do not assume the old free E5 sandbox is still open.
- **Outbound internet from the sync server.** This is the catch: Entra Connect needs HTTPS to Microsoft, but the lab DC lives on the isolated host-only `VMnet1`. Run the sync on a member server that has a routed path out (the pfSense LAN), or add a second NATed NIC to a dedicated sync VM. Do not move the DC itself off its lab DNS rules.
- A **cloud-only account** with the **Hybrid Identity Administrator** role for the install (for example `admin@<tenant>.onmicrosoft.com`). (Why cloud-only: if the admin you sign in with is itself a synced account, a sync problem can lock you out of fixing it.)

!!! note "Entra Connect Sync vs Entra Cloud Sync"
    Two tools do this. **Entra Connect Sync** is the full agent on a Windows server (the classic Azure AD Connect). **Entra Cloud Sync** is a lighter, cloud-managed agent that fits a single small domain like this lab. This page uses Connect Sync because the brief names it; Cloud Sync is the simpler option if you only need user/password sync. [VERIFY] current product names and download locations, since Microsoft renames these often.

## Steps

### Part 1: Fix UPNs before you sync

1. `corp.lab` is non-routable, so Entra cannot verify it and will rewrite synced sign-in names to `<tenant>.onmicrosoft.com`. Add a routable UPN suffix first. If you own a public domain, add it; otherwise use the tenant's `onmicrosoft.com` name.

   ```powershell
   # On DC01: add an alternate UPN suffix
   Set-ADForest -Identity corp.lab -UPNSuffixes @{add="weaverlab.example"}   # use a domain you control or the onmicrosoft.com name
   ```

2. Set each sync-scoped user's UPN to that routable suffix:

   ```powershell
   Get-ADUser -Filter * -SearchBase "OU=Departments,DC=corp,DC=lab" |
       ForEach-Object {
           Set-ADUser $_ -UserPrincipalName ("{0}@weaverlab.example" -f $_.SamAccountName)
       }
   ```

   (Why first: fixing UPNs after the initial sync means re-stamping every cloud object, which is slower and error-prone.)

### Part 2: Install and configure Entra Connect

3. On the sync server (the internet-capable member server), download **Microsoft Entra Connect** from Microsoft and run it. Choose **Express Settings** for the lab default. [VERIFY] the current download URL.
4. When prompted for the sign-in method, choose **Password Hash Synchronization (PHS)**. (Why PHS: it is the simplest resilient option, keeps working if the on-prem box is down, and needs no extra infrastructure. Pass-through auth and federation are heavier and out of scope here.)
5. Optionally enable **Seamless single sign-on** so domain-joined clients get silent cloud sign-in.
6. Provide on-prem **Enterprise Admin** credentials (to create the sync service account) and the cloud **Hybrid Identity Administrator** account.
7. **Scope the sync to `OU=Departments`** only. Filter out `Builtin`, `Users`, service, and admin OUs. (Why scope: you never sync the whole directory; built-in and privileged accounts do not belong in the cloud copy.)
8. Finish the wizard and let the initial sync run.

### Part 3: Force and watch the sync

9. From the sync server:

   ```powershell
   Import-Module ADSync
   Get-ADSyncScheduler                       # confirm sync is enabled, see the interval
   Start-ADSyncSyncCycle -PolicyType Initial # force a full sync now
   ```

## Verify

- In the **Microsoft Entra admin center**, open Users. The Departments accounts appear with **On-premises sync enabled = Yes** and source **Windows Server AD**.
- From the sync server, confirm objects exported without error:

  ```powershell
  Get-ADSyncConnectorRunStatus
  ```

- Sign in at `https://myapps.microsoft.com` as a synced user (for example `jsmith@weaverlab.example`) with the on-prem password. A successful sign-in proves the password hash synced.

!!! success "Pass criteria"
    - The Departments users (and only those) show as directory-synced in Entra ID.
    - A synced user signs into the cloud with their on-prem password.
    - `Get-ADSyncScheduler` shows sync enabled and a recent successful cycle.

## Snapshot

Snapshot the sync server **before** the install (`pre-entra-connect`). (Why before: Entra Connect installs SQL Express, a service account, and scheduled sync; rolling the install back cleanly is far easier from a snapshot than by uninstalling. Synced objects also persist in the cloud after an uninstall and need manual cleanup.)

## Gotchas

!!! danger "Non-routable domain: fix UPN suffixes first"
    You cannot verify `corp.lab` in Entra. If you sync before fixing UPNs, every user lands in the cloud as `name@<tenant>.onmicrosoft.com`. Add a routable UPN suffix and re-stamp users in Part 1, then sync.

!!! warning "Free tier limits what hybrid identity can do"
    Entra ID Free covers directory sync and PHS. **Password writeback** (cloud password resets flowing back on-prem), **Conditional Access**, and group-based licensing need **Entra ID P1/P2**. Plan around the free edition; do not assume writeback works. [VERIFY] the current free vs P1 feature split.

!!! warning "The sync server still follows the lab DNS rule"
    If the sync server is domain-joined, its DNS must point at the DC (`192.168.100.5`), and the **DC** forwards external lookups out through pfSense. Pointing the member server straight at `8.8.8.8` breaks domain logon. Internet for Entra Connect comes through the forwarder, not by bypassing AD DNS.

!!! warning "Scope the sync, every time"
    An unscoped sync pushes Builtin and privileged accounts to the cloud. Always restrict the sync to `OU=Departments` (or the specific OUs you intend), and re-check the scope after any Entra Connect upgrade.

## What this sets up

This is the on-prem-to-cloud bridge. The same synced identities secure cloud workloads in the **[Next Lab Series](../next-lab-series.md)**: AI Security Lab Phase 4 puts an Azure AI service behind these Entra accounts with RBAC and private endpoints. Hybrid identity here is also the foundation the Microsoft cloud and AI security path (exam SC-500) assumes.
