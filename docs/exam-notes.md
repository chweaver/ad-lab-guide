# Exam notes (A+ 220-1202 objective 2.2)

CompTIA A+ Core 2 objective 2.2 covers Active Directory at a help-desk level. CompTIA tests definitions and distinctions, not console wizardry. The lab gives you the muscle memory. This page gives you the vocabulary they ask about.

## Objective 2.2 topic checklist

- Login script
- Domain
- Group Policy / updates
- Organizational units (OUs)
- Home folder
- Folder redirection
- Security groups

That is the entire 2.2 sub-objective. Everything below maps to those terms.

## Active Directory in one paragraph

Active Directory is Microsoft's directory service. A **domain controller** (DC) hosts a database of **objects**: users, computers, groups, OUs. Clients authenticate against the DC instead of using local accounts. A **domain** is the unit of administration. A **forest** is one or more domains sharing a schema. In the lab, `corp.lab` is a single domain in its own forest.

## Group Policy

- **GPO** (Group Policy Object) is a bundle of settings that gets applied to users or computers.
- **GPOs link to**: sites, domains, and OUs. Plus a special category "starter GPOs".
- **GPOs do NOT link to**: the built-in `CN=Users` or `CN=Computers` containers. **This distinction is a common exam trap.** Move new accounts out of `CN=Users` into an OU if you want policy to hit them.
- **Processing order**: Local → Site → Domain → OU (LSDOU). The last one wins by default.
- **Refresh**: clients pull policy on logon and roughly every 90 minutes after that, with a random 30-minute offset. Force it with `gpupdate /force`.
- **Inspect**: `gpresult /r` on the client shows which GPOs applied to the current user and computer.

## Organizational units (OUs)

- A container inside a domain that holds users, computers, and groups.
- Two purposes: **delegate admin** (give help-desk control over one OU only) and **target GPOs** (link policy to one OU instead of the whole domain).
- OUs are different from the default **containers** (`CN=Users`, `CN=Computers`). GPOs cannot link to containers.

## Security groups vs distribution groups

| Group type | Used for | Has a SID? | Can hold permissions? |
|------------|----------|------------|------------------------|
| Security | Permissions and (optionally) email | Yes | Yes |
| Distribution | Email only | No | No |

CompTIA cares that you know **security groups grant access, distribution groups send mail**.

## Group scope (AGDLP)

The lab uses AGDLP. The exam may not ask "what does AGDLP mean" but it does ask you to recognise the pattern.

| Scope | Can contain | Can be a member of | Used for |
|-------|-------------|--------------------|----------|
| Global | Accounts and other Global groups from the same domain | Universal and Domain Local groups in any domain | Group **users** by role |
| Domain Local | Accounts, Global, Universal, other Domain Local (same domain) | Other Domain Local groups in the same domain | Apply **permissions** to a resource |
| Universal | Accounts, Global, other Universal | Universal and Domain Local groups in any domain | Span domains (rare in a single-domain lab) |

**AGDLP one-liner**: put **A**ccounts into **G**lobal groups, nest those into **D**omain **L**ocal groups, assign **P**ermissions to the Domain Local groups. Never put permissions on a Global group, and never put users directly on a resource ACL.

## Home folder vs folder redirection (exam favourite)

CompTIA loves this pair because they sound similar but solve different problems.

| Feature | Home folder | Folder redirection |
|---------|-------------|---------------------|
| Configured on | The user object (Profile tab) | A Group Policy Object |
| What it does | Maps a drive letter (typically `H:`) to a per-user network folder | Replaces specific local folders (Documents, Desktop, Pictures...) with network paths |
| User-visible result | A new drive letter | The same `Documents` folder, but the contents live on the server |
| Use case | A general scratch space | Make user data follow the user across machines, surviving reimage |
| Typical path pattern | `\\DC01\Home$\%username%` | `\\DC01\Redirect$\<username>\Documents` |

Both are network-backed. Both can be backed up centrally. The difference is **where you configure it** (user object vs GPO) and **what it redirects** (a drive letter vs specific named folders).

## Login scripts

- A script (`.bat`, `.cmd`, `.ps1`) that runs at user logon.
- Two ways to assign:
  - **User object**: Profile tab, Logon script field. Script must live in `\\<domain>\SYSVOL\<domain>\scripts\` (the NETLOGON share).
  - **GPO**: User Configuration > Policies > Windows Settings > Scripts (Logon/Logoff). The modern way.
- Common uses: map a drive, print a banner, sync the time, set environment variables.
- For drive mapping specifically, **Group Policy Preferences > Drive Maps** is preferred over a script.

## Domain join checklist (and why each step matters)

1. **DNS first**. Point the client at the DC's IP. A domain join is a DNS-driven discovery. No DNS, no join.
2. **Time within 5 minutes**. Kerberos rejects tickets that drift further. Domain-joined machines sync time from the PDC emulator automatically afterward.
3. **Network reachable**. Same subnet or routed path to the DC on TCP/UDP 53 (DNS), 88 (Kerberos), 389/636 (LDAP), 445 (SMB), 135 + dynamic RPC.
4. **Hostname not already in use**. Rename the client to something unique before joining.
5. **A domain credential authorised to join**. Domain Admin works; in production you delegate "add computer to domain" to a help-desk group.

## Account management terms

- **Disable** vs **delete**: disable first. A disabled account keeps SIDs and group memberships, so you can re-enable it. A deleted account is gone; re-creating with the same name produces a new SID.
- **Account lockout**: triggered by too many bad passwords (default in many environments: 5 to 10 attempts, 15-minute lockout window). Unlock from ADUC or with `Unlock-ADAccount`.
- **Password reset** vs **password change**: a help-desk **reset** does not require the old password. A user **change** does.
- **Move object**: drag to a new OU in ADUC, or `Move-ADObject` in PowerShell. Moving changes the DN and therefore which GPOs apply.

## Quick exam traps

!!! danger "GPOs do not link to `CN=Users`"
    They link to sites, domains, and OUs. If a user is sitting in the default `Users` container, no OU-linked GPO will hit them.

!!! danger "Security group ≠ distribution group"
    Distribution groups have no SID and grant zero access. If the question is about permissions, it is a **security** group.

!!! danger "Home folder ≠ folder redirection"
    Home folder = drive letter, set on the user object. Folder redirection = named folders (Documents, Desktop), set via GPO.

!!! danger "Local accounts are not AD accounts"
    A user logged in with a local Windows account (`.\administrator`) is not authenticating against the domain. CompTIA likes asking you to spot this.
