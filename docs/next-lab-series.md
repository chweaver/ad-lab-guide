# Next Lab Series: AI Security

You built a domain, hardened it with Group Policy, made it resilient with a second DC, and extended it to the cloud with Entra Connect. The next series turns the same homelab into an **AI security lab**: stand up a local model, attack it, defend it, then secure cloud AI with the identities you just synced.

It is one continuous path, not a fresh start. AD foundations (Phases 1-7), then hybrid identity (Phases 16-17), then AI security. The AI series reuses the same pfSense subnets and the `corp.lab` domain, and adds a dedicated GPU server for the heavier phases. Tooling stays free or near-free.

## The arc (six phases)

| Phase | Focus | Runs on | Supports |
|---|---|---|---|
| 1 | Local LLM baseline + inference attack surface | 4070 Ti rig today | AI infrastructure awareness |
| 2 | Prompt injection, jailbreak, data exfiltration | 4070 Ti rig today | securing AI workloads, AI risk |
| 3 | Defenses: input/output filtering, prompt hardening, traffic monitoring | 4070 Ti rig today | secure compute and monitoring |
| 4 | Azure AI service locked down with Entra ID, RBAC, private endpoints | Cloud + any VM | identity and access for AI |
| 5 | Governance artifacts: model inventory, risk assessment, acceptable-use policy | No GPU needed | AI governance |
| 6 | Detection and response: inference logs into Wazuh/Grafana, anomaly rules | 5090 server | posture monitoring, logging, IR |

**Phase 4 picks up exactly where [Phase 17 (Entra Connect)](stretch/phase-17-entra-connect.md) leaves off:** the Entra tenant and synced identities become the access control for a cloud AI service.

## Companion docs

These ship alongside the lab series (published separately, not part of this site yet):

- **AI Security Lab guide** (`AI-Lab1-Foundations.md`): the step-by-step build, same format as this guide.
- **AI Security Certification Roadmap** (`ai-cert-roadmap.md`): the certs these phases map to, sequenced after CCNA. In short: **SC-500** (Cloud and AI Security Engineer Associate) first, then **IAPP AIGP**, then **SANS GCAD / SEC549**, with **NVIDIA NCA-AIIO** last and conditional on doing real GPU work.

## Why this order

Security work on AI only makes sense once you can run AI. The series builds the thing, breaks it, defends it, then moves the lesson into the cloud where the money and the certs are. See the [Lab Map](lab-map.md) for how every phase connects.
