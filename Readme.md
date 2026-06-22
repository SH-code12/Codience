# Codience — *Sudonators Team* ^_^

> **AI-powered pull-request prioritization, risk analysis, and reviewer recommendation — right inside VS Code.**

Codience helps developers and tech leads answer one question fast: **“Which pull request should we review and merge next?”** It analyzes every open PR for **business impact**, **bug risk**, **change complexity**, and **reviewer fit**, then surfaces ranked, data-driven recommendations in an in-editor dashboard.

---

## Abstract
Codience is an intelligent VS Code extension that helps engineering teams decide what to work on next by combining machine learning, large language models, and software-engineering metrics. It connects to GitHub and Jira, scores each open pull request across multiple dimensions, recommends the best reviewers, and summarizes changes — all without leaving the editor.

---

## What Codience Does

| Capability | How it works |
|---|---|
| **Business-impact ranking** | Scores each PR (blast radius, user exposure, deadline pressure, business impact) into **High / Medium / Low** tiers and flags merges that should be blocked. |
| **Bug-risk analysis** | An SVM model trained on commit-level metrics (ApacheJIT-style features) predicts a **bug probability** for each PR. |
| **Reviewer recommendation** | A RAG + multi-agent engine matches PR changes to the most qualified reviewers using commit history, skill extraction, Jira workload, and vector similarity. |
| **PR summarization** | An LLM produces a concise, human-readable summary of large diffs (with map-reduce for big PRs). |
| **Jira & GitHub integration** | OAuth into both; link PRs to tickets, read assignments, and enrich scoring with real project context. |
| **In-editor dashboard** | A React webview shows ranked PRs, risk/impact charts, recommended reviewers, and profile analytics inside the VS Code sidebar. |

---

## Architecture

Codience is a **polyglot microservices system**. A VS Code extension hosts a React dashboard that talks to a .NET Core API and four Python FastAPI services.

```
                 ┌───────────────────────────────────────────┐
                 │   VS Code Extension  (React + Vite webview) │
                 │   Dashboard · PR table · Reviewers · Jira   │
                 └───────────────┬─────────────────────────────┘
                                 │ HTTP
        ┌────────────────────────┼─────────────────────────────────────┐
        ▼                        ▼                                       ▼
┌────────────────┐   ┌──────────────────────┐   ┌──────────────────────────────────┐
│  .NET Core API │   │  Python AI services  │   │           External APIs          │
│  ASP.NET 9     │   │  (FastAPI)           │   │                                  │
│  EF Core       │   │  • Reviewer  :8000   │   │  GitHub REST · Jira Cloud        │
│  :5051 / :8080 │   │  • Risk      :8001   │   │  Ollama · Gemini · Groq/Mistral  │
│                │   │  • Summarizer:8002   │   │  Chroma vector DB                │
│                │   │  • Impact    :8003   │   │                                  │
└───────┬────────┘   └──────────────────────┘   └──────────────────────────────────┘
        │
        ▼
  PostgreSQL 16
```

A detailed, as-built **UML class diagram** of the whole system lives in
`../Diagrams/Codience_AsBuilt_ClassDiagram.drawio` (5 pages: overview, backend, frontend, reviewer engine, AI services).

### Components

- **Frontend** — VS Code extension with a React + Vite webview (`SidebarProvider`). Pages: Dashboard, PRs, PR summary, reviewer settings, Jira login, profile. Calls every backend service via typed service modules.
- **.NET API** — ASP.NET Core 9 in clean architecture (Domain → Abstraction → Services → Infrastructure → API) with EF Core + PostgreSQL. Handles GitHub OAuth/App/webhooks, Jira OAuth, repositories & pull requests, and computes change/history/experience metrics.
- **Reviewer Recommender** (FastAPI, `:8000`) — RAG + multi-agent: PR skill extraction, Chroma vector search over commit diffs, Tversky profile matching, Jira-workload analysis, and a resilient multi-provider LLM router (Groq / Mistral / Cerebras / Gemini) with a two-layer profile cache.
- **Risk Service** (FastAPI, `:8001`) — SVM model (`svm_model_proba.pkl`) over 12 log-transformed commit metrics → bug probability.
- **PR Summarizer** (FastAPI, `:8002`) — Google Gemini, single-call or map-reduce summarization of PR diffs.
- **Business Impact / Priority** (FastAPI, `:8003`) — blends a rule-based formula with a local Qwen2.5-Coder model (via Ollama) to score blast radius, user exposure, and deadline pressure into an impact tier.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | TypeScript, React, Vite, VS Code Extension API, Recharts |
| **Backend** | C#, ASP.NET Core 9, Entity Framework Core |
| **AI / ML** | Python, FastAPI, scikit-learn (SVM), Chroma, Sentence-Transformers (nomic / MiniLM), Ollama (Qwen2.5-Coder, Qwen2.5), Google Gemini, Groq / Mistral / Cerebras |
| **Database** | PostgreSQL 16 |
| **Integrations** | GitHub REST API & GitHub App, Jira Cloud API |
| **DevOps** | Docker, docker-compose, GitHub Actions |

---

## Repository Layout (branches)

This work spans several branches of the GitHub repository:

| Branch | Contents |
|---|---|
| `Backend` | ASP.NET Core API (this checkout) |
| `frontend_v2` | React + Vite VS Code webview (latest UI) |
| `AI/DL` | Risk service, PR Summarizer, Reviewer Recommender engine |
| `Backend-AI` | Business Impact / Priority service |
| `DevOps` | Dockerfiles & `docker-compose` |
| `main` | Integration branch |

---

## Getting Started

> Prerequisites: .NET 9 SDK, Node.js 18+, Python 3.10+, PostgreSQL 16, and (optionally) Ollama for the local LLM scoring.

**1. Backend API**
```bash
cd Backend/API
dotnet restore
# set ConnectionStrings__DefaultConnection for PostgreSQL
dotnet run            # serves on http://localhost:5051
```

**2. Python AI services** (each in its own terminal / venv)
```bash
# Risk (:8001), Summarizer (:8002), Reviewer (:8000), Business Impact (:8003)
pip install -r requirements.txt
uvicorn app:app --port <port>
```

**3. Frontend (VS Code extension)**
```bash
cd codience
npm install
npm run watch         # then press F5 in VS Code to launch the extension host
```

**4. Or run the containerized stack**
```bash
docker compose up     # db + api + frontend (see DevOps branch)
```

---

## Objectives
- Reduce bottlenecks in development workflows.
- Improve delivery speed and efficiency.
- Ensure the highest-priority work gets reviewed and merged first.
- Provide data-driven recommendations directly inside the code editor.

## Expected Outcomes
- Less time spent deciding what to review next.
- Faster delivery cycles with fewer bottlenecks.
- Better alignment of work with business priorities and team skills.
- Higher code quality by surfacing risky changes early.
- Data-driven decisions replacing guesswork in prioritization.

---

## Mentorship
- **Academic Supervisors:**
  - Dr. Mohamed El Ramly
  - TA: Hager Mahmoud

---

*Faculty of Computers and Artificial Intelligence — Graduation Project.*
