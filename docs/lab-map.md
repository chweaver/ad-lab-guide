# Lab Map

One screen, the whole path. Green is done, amber is the current phase, grey is planned, blue is stretch, teal is the next series. Solid arrows are hard dependencies; dotted arrows are softer ones; thick arrows are the bridge into AI security.

```mermaid
flowchart TD
    classDef done fill:#2e7d32,stroke:#1b5e20,color:#fff
    classDef next fill:#f9a825,stroke:#f57f17,color:#000
    classDef planned fill:#455a64,stroke:#263238,color:#fff
    classDef stretch fill:#1565c0,stroke:#0d47a1,color:#fff
    classDef ai fill:#00838f,stroke:#004d40,color:#fff

    subgraph BUILD["Build-out: A+ Core 2 core"]
        direction TB
        P1["1 Build the DC"] --> P2["2 OUs, users, AGDLP"]
        P2 --> P3["3 Join client WS01"]
        P3 --> P4["4 Group Policy"]
        P4 --> P5["5 File services"]
        P5 --> P6["6 Login scripts + drive maps (NEXT)"]
        P6 --> P7["7 Help-desk drills"]
    end

    subgraph PLANNED["Planned: Security+ depth"]
        direction TB
        P8["8 GPO security baseline"]
        P9["9 Departmental file server"]
        P10["10 Scripted patching"]
        P15["15 AD backup + restore"]
        P16["16 DC02 on Server 2025 + replication"]
    end

    subgraph STRETCH["Stretch: MSP depth"]
        direction TB
        P13["13 DHCP role"]
        P14["14 RDP / remote access"]
        P17["17 Entra Connect hybrid identity"]
    end

    subgraph AISEC["Next series: AI Security Lab"]
        direction TB
        A1["1 Local LLM baseline"] --> A2["2 Prompt injection"]
        A2 --> A3["3 Defenses + monitoring"]
        A3 --> A4["4 Azure AI + Entra lockdown"]
        A4 --> A5["5 Governance artifacts"]
        A5 --> A6["6 Detection + response"]
    end

    P4 -.-> P8
    P5 -.-> P9
    P5 -.-> P10
    P7 -.-> P15
    P4 -.-> P16
    P4 -.-> P13
    P4 -.-> P14
    P16 --> P17
    P7 ==> A1
    P17 ==> A4

    class P1,P2,P3,P4,P5 done
    class P6 next
    class P7,P8,P9,P10,P15,P16 planned
    class P13,P14,P17 stretch
    class A1,A2,A3,A4,A5,A6 ai
```

## Where you are

Phases 1 through 5 are complete: a healthy `corp.lab` domain with OUs, users, AGDLP groups, a domain-joined client, Group Policy, file shares, and redirected home folders. **Phase 6 (login scripts and drive maps) is the current step.** The live counter on the [Home](index.md) page is the source of truth.

## How the tracks relate

- **Build-out (1-7)** is the A+ Core 2 core. Each phase assumes the prior one finished cleanly.
- **Planned (8-10, 15-16)** is the committed roadmap, sequenced for Security+ (SY0-701): hardening, least-privilege file services, patching, recovery, and resilience. Phases 15 and 16 keep their original numbers from the old stretch track so existing links stay valid.
- **Stretch (13-14, 17)** is optional MSP depth. DHCP and RDP branch off a working domain independently. The second DC (16) and Entra Connect (17) form the hybrid-identity chain.
- **AI Security Lab** is the next guide. It reuses this same homelab. Two bridges connect the tracks: finishing the AD build-out leads into the local-LLM work, and Entra Connect (17) feeds directly into securing a cloud AI service with these synced identities (AI Phase 4). See [Next Lab Series](next-lab-series.md).
