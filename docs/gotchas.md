# Gotchas

Every pitfall from every phase, aggregated. Skim this before starting a phase. If you hit something not on the list, add it.

## Networking and DNS

!!! danger "Client DNS must point at the DC, never at the host or the internet"
    A client at `192.168.100.20` with DNS set to `8.8.8.8` cannot resolve `corp.lab` or discover the DC. Domain join will silently fail with a vague "domain not found" message. Always set the client's preferred DNS to `192.168.100.5` (DC01) **before** the join.

!!! warning "DC's own DNS points at 127.0.0.1"
    Not at the gateway, not at another DC. The DC resolves its own domain through itself. This is the single most common misconfiguration in lab DC builds.

!!! danger "Do not use `.local` for the domain DNS name"
    Apple's Bonjour service uses `.local` for mDNS. Mixing it with AD breaks name resolution on any client running iTunes, AirPrint, or even some Visual Studio installers. Use `.lab`, `.test`, or a domain you actually own.

!!! warning "Disable VMware DHCP on VMnet1"
    VMware Workstation ships VMnet1 with DHCP enabled. With static lab IPs you do not want a rogue DHCP server handing out leases on the same subnet. Disable it in `Edit > Virtual Network Editor`.

## Hostnames and joins

!!! warning "Rename the client BEFORE joining the domain"
    If you join while named `DESKTOP-ABC123`, AD captures that name. Renaming after join is a domain operation that requires extra cleanup. Rename to `WS01` first, reboot, then join.

!!! warning "Clock drift over 5 minutes kills Kerberos"
    Domain join fails with "the trust relationship..." or "clock skew too great". Sync the client to the DC's time before joining. Domain-joined machines sync from the PDC emulator automatically afterward.

!!! danger "Domain join needs an account with rights to add computers"
    Out of the box, any authenticated domain user can join up to 10 computers. After that, you need an account with "Add workstations to domain" rights. For lab use, just use Domain Admin.

## AD structure

!!! warning "Do not name a custom OU `Users`"
    The domain already has a built-in `CN=Users` **container** at the root. Creating an `OU=Users` next to it creates a confusing namespace collision in tools and PowerShell paths. The lab uses `Departments` as the parent OU.

!!! danger "GPOs link to OUs, not to `CN=Users` or `CN=Computers`"
    New accounts land in the built-in `CN=Users` container by default. No OU-linked policy will touch them there. Move accounts into an OU as part of provisioning, or use `redirusr.exe` and `redircmp.exe` to retarget the defaults.

!!! warning "Containers (`CN=...`) and OUs (`OU=...`) look the same in ADUC"
    Toggle **View > Advanced Features** in ADUC to see them clearly. Containers have a folder icon with no compass; OUs have a folder with a compass overlay.

## Groups and permissions

!!! danger "Never assign permissions to a Global group directly"
    The whole point of AGDLP is decoupling membership from permission. Putting an ACE on `IT-Staff` directly works but pollutes the model. Always go through the matching `*-Share-RW` (Domain Local) group.

!!! warning "Distribution groups grant no access"
    If you accidentally create a Distribution group and assign it to an ACL, the GUI accepts it but it does nothing. Always pick **Security**.

!!! warning "Group scope cannot be changed freely"
    You cannot convert Global directly to Domain Local. You go Global → Universal → Domain Local. Plan the scope when you create it.

## File shares and NTFS

!!! warning "Share permissions and NTFS permissions both apply"
    The **effective** permission is the most restrictive of the two. Best practice: set share permissions to `Authenticated Users: Change` (or `Everyone: Full` if you trust the network) and let NTFS do the real work.

!!! danger "Trailing `$` hides the share, it does not secure it"
    `\\DC01\Home$` does not appear in network browse listings, but anyone who knows the path can connect. Permissions, not obscurity, secure data.

!!! warning "Home folder auto-create needs the right NTFS pattern"
    The folder under `Home$` is created automatically when you set the user's profile path, but only if the share's NTFS allows `Authenticated Users: Create Folder / Append Data` on the root and `Creator Owner: Full Control` on subfolders. Get this wrong and the folder is created but the user cannot write to it.

## Group Policy

!!! warning "GPO inheritance is OU-deep, not just one level"
    A GPO linked to `OU=Departments` applies to users in `OU=IT,OU=Departments` unless blocked. Use **Block Inheritance** or **Security Filtering** to scope down, never to rebuild the same GPO twice.

!!! warning "`gpupdate /force` does not always reapply everything"
    Some settings (drive maps, folder redirection, software install) require a **logoff/logon** or a full reboot to take effect, even after a forced update. When in doubt, log off.

!!! warning "Folder Redirection setup ordering matters"
    If you redirect Documents to a share whose NTFS is wrong, the GPO succeeds but the user loses access to their own folder. Always test on one user before rolling out.

## Snapshots and rollbacks

!!! tip "Snapshot before promoting the DC, before linking a new GPO, before joining a client"
    These are the moments where a small mistake takes the longest to undo. A 5-second snapshot saves a 30-minute rebuild.

!!! danger "Do not snapshot a DC and roll it back after replication starts"
    With a single DC in the lab this is harmless. With two or more (Phase 16), rolling back a DC introduces a **USN rollback** that breaks replication. Use AD-aware backup tools instead.

## VMware Tools and the DC

!!! warning "Install VMware Tools BEFORE promoting to DC"
    Tools installs a paravirtual NIC driver and time sync. Doing it after promotion sometimes flips DNS or registers unwanted host names in AD-integrated DNS. Tools first, snapshot, then promote.

!!! warning "Do not enable VMware host-to-guest time sync on a DC"
    Domain controllers, especially the PDC emulator, should be the authoritative time source for the domain. Host-time-sync can fight Windows Time and cause Kerberos drift. Uncheck it in VM Options > VMware Tools.
