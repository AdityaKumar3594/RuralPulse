# Ruralpulse — learning to livelihood

AI-powered platform helping rural Indian students (Class 9 to graduation) discover careers, plan
learning pathways and find grounded opportunities, with teacher/facilitator support.
Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Prerequisites

Docker, [uv](https://docs.astral.sh/uv/), Node 22.22+.

## Run the prototype (one command)

Needs Docker Desktop (running), [uv](https://docs.astral.sh/uv/) and Node 22+.

```sh
make run
```

This starts PostgreSQL, applies the migrations, loads the curated careers/sources/opportunities,
creates the demo accounts, and starts the API (`:8100`) and the web app. Then open
**http://localhost:5173**. Stop with `make stop`.

### Demo logins (throw-away; never use on a real deployment)

| Who | Phone | PIN | What to try |
|---|---|---|---|
| Student Asha (15, Tamil) | 9000000011 | 1234 | Filled profile, shares with her teacher: recommendations, pathway, eligibility |
| Student Karthik (20, English) | 9000000012 | 1234 | Empty profile: do the interview; has *not* shared with the teacher |
| Facilitator | 9000000002 | 12345678 | Dashboard, observations, endorsements, help requests |
| Partner | 9000000003 | 12345678 | Create a provider, submit an opportunity |
| Admin | 9000000001 | 12345678 | Approve providers, review submissions, assign teachers |

### Switching on the AI (optional)

Without a key everything works with fixed wording. To let Claude rewrite explanations
(always checked against the facts), put this in `backend/.env` and re-run `make run`:

```
LLM_PROVIDER=anthropic
LLM_API_KEY=<your key>
```

Voice (BHASHINI) additionally needs `BHASHINI_USER_ID` and `BHASHINI_API_KEY`; it has not been
tested against the live service.

### What is real and what is not

- Real: accounts and consent, interview, profile with provenance, career catalog (30 careers,
  an unverified draft), 9 hand-checked source records, keyword search, deterministic eligibility,
  explainable ranking, pathways, facilitator and partner workflows, application tracking.
- Not live-tested: Claude calls (no key was available while building) and BHASHINI voice.
- Not built: offline mode (out of scope), payments (paid training modules stay locked), real
  employer/mentor listings (none are invented).

## Develop



```sh
make install
cp backend/.env.example backend/.env
make db-up        # Postgres in Docker (creates Ruralpulse and Ruralpulse_test)
make migrate
make dev-backend  # http://localhost:8100/api/health, docs at /api/docs
make dev-frontend # http://localhost:5173
```

## Checks

```sh
make lint   # ruff, eslint, tsc
make test   # pytest (incl. database tests) + vitest
make build  # production frontend build
```
