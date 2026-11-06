# VouchAI: Credit That Learns

VouchAI is an autonomous credit underwriting engine designed specifically for AI agents and agent fleets. Standard credit models rely solely on cold transactional formulas, leaving lenders blind to emerging fleet risks, sudden default clusters, or identity evasion. VouchAI solves this by coupling a mathematical reputation formula with continuous semantic memory provided by Hindsight and an LLM synthesis underwriter.

---

## Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │               Applicant Agent                │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │            Identity Security Gate            │
                    │   - Rule 1: Lookalike name impersonation     │
                    │   - Rule 2: Anti-name-washing detection      │
                    └──────────────┬───────────────────────────────┘
                                   │ Passed
                                   ▼
          ┌────────────────────────┴────────────────────────┐
          │                                                 │
          ▼                                                 ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Formula Underwriting        │       │         Hindsight Memory        │
│  - Task success rate (35 pts)   │       │  - Semantic recall of fleet     │
│  - Spend regularity (15 pts)    │       │    and category default history │
│  - Loan repayment history (40)  │       │  - Tagged by principal/category │
│  - Cold-start limit: $50        │       │  - Automatic belief reflection  │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 └────────────────► ◄──────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────────────────┐
                    │                LLM Underwriter               │
                    │      Synthesizes formula baseline with       │
                    │      memory beliefs to set multiplier        │
                    │       (Final Limit = Formula × Mult)         │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │          Resolved Loan / Retain Loop         │
                    │   Outcomes (repaid/defaulted) continuously   │
                    │      retained into Hindsight memory          │
                    └──────────────────────────────────────────────┘
```

### Where Hindsight Sits
Hindsight is the continuous memory layer of VouchAI. When an agent requests credit:
1. `recall_context` retrieves historical observations and default facts filtered by `[principal, category]` tags.
2. The LLM underwriter incorporates these recalled facts into its final assessment, adjusting the multiplier (e.g. cutting credit limit by 90% or denying entirely if high cluster risk is detected).
3. When loans are resolved (or imported via CSV), `retain_outcome` feeds the final repayment or default outcome back into Hindsight.
4. Over time, Hindsight updates its beliefs about which fleets and categories present elevated risk.

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python -m app.seed
```

To run the API server:
```bash
uvicorn app.main:app --reload --port 8000
```
API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to interact with the dashboard.

---

## Environment Variables

Copy `.env.example` to `.env` (or configure in your deployment):

```bash
# Hindsight memory configuration
HINDSIGHT_BASE_URL=https://api.hindsight.example.com
HINDSIGHT_API_KEY=your_hindsight_api_key

# Groq LLM underwriter
GROQ_API_KEY=your_groq_api_key

# Admin API key protection (optional)
# When set, requires header "X-API-Key" on /import/*, /sim/run, and /loans/{id}/resolve
ADMIN_KEY=your_secret_admin_key
NEXT_PUBLIC_ADMIN_KEY=your_secret_admin_key

# Frontend API target
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

---

## CSV Ingestion Formats

VouchAI supports importing operational tasks and historical loans via the `/import` UI or REST endpoints.

### Tasks CSV (`POST /import/tasks`)
Ingests task execution history to establish agent track records.

```csv
agent,principal,category,success,amount,ts
crawler-01,ApexAI,data-scraping,true,120.00,2026-03-01T10:00:00Z
crawler-01,ApexAI,data-scraping,true,150.00,2026-03-02T11:00:00Z
docu-writer,LedgerLeaf,report-writing,true,200.00,2026-03-01T12:00:00Z
```

- **Required columns:** `agent`, `principal`, `category`, `success` (`true`/`false`), `amount` (number > 0).
- **Optional column:** `ts` (ISO-8601 timestamp, defaults to UTC now).
- **Option `?replace=true`:** Clears existing database records before import (local dev only).
- **Validation:** Files up to 2 MB, UTF-8. Row errors are recorded in `rejected` with exact line numbers and reasons while valid rows are saved.
- **Identity rule:** An agent name cannot change its principal fleet. Any conflict is rejected.

### Loans CSV (`POST /import/loans`)
Ingests historical loans with resolution outcomes.

```csv
agent,principal,category,amount,outcome
crawler-01,ApexAI,data-scraping,250.00,repaid
scraper-07,NovaOps,data-scraping,400.00,defaulted
```

- **Required columns:** `agent`, `principal`, `category`, `amount` (> 0), `outcome` (`repaid` or `defaulted`).
- **Option `?teach_memory=true`:** Retains every imported outcome directly into Hindsight memory.

---

## Identity Gate Rules

Autonomous agents can be spun up in seconds, making standard reputation systems vulnerable to impersonation and name washing. The identity gate (`backend/app/services/identity.py`) runs before formula calculations and before LLM/Hindsight calls:

1. **Rule 1: Lookalike Impersonation:**
   - Normalizes names by stripping non-alphanumeric characters and converting to lowercase (e.g. `scraper-07` -> `scraper07`).
   - If an agent shares a normalized name with an agent owned by another principal, loan origination is denied immediately.
2. **Rule 2: Anti-Name Washing:**
   - Detects fleet owners attempting to discard tainted reputations by launching "fresh" agents.
   - If an agent has fewer than 5 own records (tasks + resolved loans) AND its parent principal fleet already has 2 or more defaults, the application is blocked.

When triggered, the loan is saved as `denied` with `identity_blocked=true` without calling LLMs or memory APIs.

---

## Running the Simulator

VouchAI includes an automated Monte Carlo simulator comparing **Memory OFF** (pure formula reputation) vs. **Memory ON** (formula + Hindsight memory).

### 1. Deterministic Fake Mode (Offline / Testing)
Simulates credit decisions locally without external API credentials:
```bash
python -c "from app.services.simulator import run_simulation, save_result; res = run_simulation(rounds=40, seed=7, fake=True); save_result(res); print('Done')"
```

### 2. Live Simulation (Real Hindsight + Groq)
Requires `HINDSIGHT_API_KEY` and `GROQ_API_KEY`:
```bash
python backend/scripts/run_sim.py --rounds 40 --seed 7
```

### 3. Copy Cached Run to Frontend
To visualize the run in the Next.js static simulation dashboard:
```bash
# From workspace root
copy data\cached_run.json frontend\public\cached_run.json
```

---

## Known Limitations

1. **Planted Simulator Test Rule:**
   The simulator benchmarks learning speed using a planted ground-truth rule (NovaOps agents in the `data-scraping` category default 75% of the time, while the baseline rate is 6%). This controlled synthetic test demonstrates that Memory ON detects localized fleet defaults much faster than formula scoring alone, but real-world defaults are non-stationary and more nuanced.
2. **Basic Alphanumeric Identity Matching:**
   The identity gate normalizes names using alphanumeric regex. While effective at catching simple typographical lookalikes and name re-use, production autonomous agent networks will require cryptographic agent signatures (e.g., decentralized identifiers or verifiable credentials signed by fleet keys).
3. **Storage:**
   The backend uses SQLite (`vouchai.db`) for lightweight self-contained operation. Production deployments should migrate to PostgreSQL with connection pooling.