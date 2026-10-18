# 0002 — Offline functionality is out of scope

Status: accepted (2026-10-18)

**Context.** The hackathon brief lists offline-first sync as a technical requirement, while also
placing villages without internet out of scope. The project owner chose to exclude offline.
**Decision.** No service worker, IndexedDB persistence, offline modes or sync queues. An internet
connection is required. We optimise for low bandwidth and low-end devices instead.
**Consequences.** Simpler, more reliable system. The pitch must state this choice explicitly, as
judges may score the brief's offline requirement.
