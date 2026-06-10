# Codeians — Pull Request Prioritization Platform

Codeians is an AI-powered platform that helps development teams prioritize open pull requests based on **risk**, **reviewer recommendation**, and **business impact**. It is delivered as a **VS Code extension** and a **web dashboard**, integrating directly with GitHub, GitLab, and Jira.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Modules](#modules)
  - [Risk Analysis](#risk-analysis)
  - [Reviewer Recommendation](#reviewer-recommendation)
  - [Business Impact (Upcoming)](#business-impact-upcoming)
- [Tech Stack](#tech-stack)
- [Integrations](#integrations)
- [API Reference](#api-reference)
- [Setup & Installation](#setup--installation)
- [Mentorship](#mentorship)

---

## Overview

When a team has many open pull requests, deciding which one to review first is often guesswork. Codeians replaces that guesswork with data-driven signals:

- **Risk Score** — how likely is this PR to introduce a bug?
- **Reviewer Match** — who on the team has the skills best suited to review this PR?
- **Business Impact** — how critical is this PR to ongoing business goals?

The platform surfaces these signals in a live dashboard inside VS Code and on a companion web app, so developers and tech leads can act on the highest-priority PRs without leaving their workflow.

---

## Features

- AI-powered pull request prioritization
- Risk scoring using an SVM model trained on the Apache JIT dataset
- Reviewer recommendation using RAG with Gemini LLMs and ChromaDB vector store
- Skill extraction from commit history and Jira tickets
- Real-time dashboard showing PR risk, best reviewer, and priority ranking
- VS Code extension with inline recommendations
- Web dashboard built with React
- Integration with GitHub, GitLab, and Jira APIs

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Client Layer                       │
│         VS Code Extension  /  React Web App          │
└───────────────────┬──────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────┐
│               .NET Core Backend API                  │
│   GitHub/GitLab Auth, PR metrics, file history,      │
│   developer experience aggregation                   │
└──────────┬────────────────────────┬──────────────────┘
           │                        │
┌──────────▼──────────┐  ┌──────────▼───────────────────┐
│  Risk Analysis API  │  │  Reviewer Recommender API     │
│  (Python FastAPI)   │  │  (Python FastAPI)             │
│                     │  │                               │
│  SVM model trained  │  │  RAG pipeline with Gemini     │
│  on Apache JIT      │  │  ChromaDB vector store        │
│  dataset            │  │  Skill extraction via LLM     │
└─────────────────────┘  └───────────────────────────────┘
```
### Risk Analysis

The risk module predicts how likely a pull request is to introduce a bug.

**Model:** Support Vector Machine (SVM) with probability calibration (`predict_proba`), also compared against a logistic regression baseline and a DistilBERT experiment.

**Dataset:** [Apache JIT dataset](https://github.com/user-data/apachejit) — a well-known Just-In-Time defect prediction dataset covering real Apache project commits.

**Input features** (JIT metrics extracted by the .NET backend from GitHub):

| Feature  | Description |
|----------|-------------|
| `la`     | Lines added |
| `ld`     | Lines deleted |
| `nf`     | Number of files modified |
| `nd`     | Number of directories modified |
| `ns`     | Number of subsystems modified |
| `ent`    | Change entropy (diffusion) |
| `ndev`   | Number of developers who touched these files |
| `age`    | Average time since last change (days) |
| `nuc`    | Number of unique last changes |
| `aexp`   | Author total experience (commits) |
| `arexp`  | Author recent experience |
| `asexp`  | Author subsystem experience |

**Output:** `bug_probability` — a float in [0, 1] indicating the probability that the PR introduces a defect.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/predict` | Direct prediction from raw feature values |
| `GET`  | `/orchestrate/{owner}/{repo}/{pull_number}` | Fetches PR metrics from .NET backend and returns risk score |

---

### Reviewer Recommendation

The reviewer module matches a pull request with the most qualified reviewers on the team.

**Approach:** Retrieval-Augmented Generation (RAG) pipeline.

1. **Skill extraction** — LLM (Gemini) reads each developer's commit history and Jira tickets to infer their technical skills.
2. **Vector store** — Skills and commit diffs are embedded and stored in a ChromaDB vector database.
3. **PR analysis** — The incoming PR is analyzed to identify the technical areas it touches.
4. **Matching** — Cosine similarity between the PR embedding and reviewer profiles produces a ranked candidate list.
5. **Multi-signal scoring** — Final ranking combines vector similarity, skill overlap, and recency signals.

**Key components:**

- `Reviewer_Engine.py` — main orchestrator class (`ReviewerRecommender`)
- `scorer_agent.py` — scores each candidate against the PR
- `multiset_engine.py` — aggregates multiple ranking signals
- `jira_agent.py` — extracts skills from Jira tickets using an LLM agent
- `commit_history_utils.py` — maps commit diffs to developer skills via LLM
- `profile_cache.py` — caches reviewer profiles to reduce redundant LLM calls

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/recommend-reviewers` | Recommend reviewers for a GitHub PR |
| `POST` | `/api/recommend/reviewer` | Match reviewer candidates against PR data |
| `POST` | `/api/orchestrator` | Profile a list of users and rank them for a PR |
| `POST` | `/api/analyze/jira-tickets` | Extract skills from Jira tickets |
| `POST` | `/api/analyze/commit-history` | Extract skills from a developer's commit history |

---

### Business Impact (Upcoming)

A third signal that will rank PRs based on how critical they are to current business objectives, derived from linked Jira epics, sprint priorities, and ticket labels.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| VS Code Extension | TypeScript |
| Web Frontend | React |
| Backend API | ASP.NET Core (.NET) |
| Risk API | Python, FastAPI |
| Reviewer API | Python, FastAPI |
| ML — Risk | scikit-learn (SVM), NumPy, pandas |
| ML — Reviewer | Google Gemini, LangChain, ChromaDB, sentence-transformers |
| Embeddings | Nomic, sentence-transformers |
| Data Storage | PostgreSQL (main), ChromaDB (vectors), Redis (cache) |
| DevOps | Docker, GitHub Actions |

---

## Integrations

| Platform | Purpose |
|----------|---------|
| **GitHub** | Fetch PR metadata, file diffs, commit history, developer experience |
| **GitLab** | Same as GitHub for GitLab-hosted repositories |
| **Jira** | Extract ticket context to enrich reviewer skill profiles |

---

### Risk API base URL
```
http://localhost:8000
```

### Reviewer Recommender API base URL
```
http://localhost:8001
```

### .NET Backend base URL
```
http://localhost:5051/api/GitHubAuth
```


### Prerequisites

- Python 3.10+
- .NET 8 SDK
- Node.js 18+ (for VS Code extension)
- Docker (optional)

### Risk API

```bash
cd Risk/API
pip install fastapi uvicorn scikit-learn numpy joblib gdown httpx
uvicorn risk_api:app --reload --port 8000
```

### Reviewer Recommender API

```bash
cd codience
pip install -r src/Reviewer_Recommender/requirements.txt
uvicorn src.app:app --reload --port 8001
```

### .NET Backend

```bash
cd Backend/API
dotnet restore
dotnet run
```

### Environment Variables

Create a `.env` file in `Backend/` with:

```
GITHUB_TOKEN=...
GITLAB_TOKEN=...
JIRA_TOKEN=...
GEMINI_API_KEY=...
```

---

## Mentorship

| Role | Name |
|------|------|
| Academic Supervisor | Dr. Mohamed El Ramly |
| Teaching Assistant | Hager Mahmoud |

---

*Codeians — built by the Sudonators team.*