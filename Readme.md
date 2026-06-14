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
- [Testing & Evaluation](#testing--evaluation)
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
- Reviewer recommendation using a multi-stage RAG pipeline with ChromaDB and Groq/Gemini LLMs
- Smart developer profile caching to minimize redundant LLM calls
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
│   developer experience aggregation, Jira bridge      │
└──────────┬────────────────────────┬──────────────────┘
           │                        │
┌──────────▼──────────┐  ┌──────────▼───────────────────┐
│  Risk Analysis API  │  │  Reviewer Recommender API     │
│  (Python FastAPI)   │  │  (Python FastAPI)             │
│                     │  │                               │
│  SVM model trained  │  │  Multi-stage RAG pipeline     │
│  on Apache JIT      │  │  Groq LLM + Gemini fallback   │
│  dataset            │  │  ChromaDB vector store        │
│                     │  │  Tversky similarity scoring   │
└─────────────────────┘  └───────────────────────────────┘
```

---

## Project Structure

```
CodienceProject/
├── Backend/                        # .NET Core backend API
│   └── API/                        # ASP.NET project — GitHub/GitLab auth & PR data endpoints
│
├── Risk/                           # Risk Analysis module
│   ├── API/
│   │   ├── risk_api.py             # FastAPI app — exposes /predict and /orchestrate endpoints
│   │   ├── risk_svm_proba_final.py # SVM model training script (probability calibrated)
│   │   ├── riskAnalysis_SVM.ipynb  # SVM model exploration notebook
│   │   ├── riskAnalysis_logistic.ipynb  # Logistic regression baseline notebook
│   │   └── risk_model_distilBert.ipynb  # DistilBERT model experiment
│   ├── Dataset/
│   │   ├── apacheJIT/              # Apache JIT dataset (train / test / total splits)
│   │   ├── pull_requests.csv       # Raw pull request data
│   │   └── pull_requests_labeled.csv  # Labeled dataset for training
│   └── Models/
│       ├── svm_model_proba.pkl     # Deployed SVM model (probability output)
│       ├── risk_svm_model.pkl      # SVM model (binary output)
│       └── risk_logistic_model.pkl # Logistic regression model
│
├── codience/                       # Reviewer Recommender module + VS Code extension
│   └── src/
│       ├── app.py                  # FastAPI entry point for reviewer recommendation API
│       ├── helpers.py              # Business logic helpers
│       ├── models.py               # Pydantic request/response models
│       ├── test_and_evaluate.py    # Unit tests and evaluation metrics
│       └── Reviewer_Recommender/
│           ├── PRNew/
│           │   ├── Reviewer_Engine.py      # Core recommendation engine / orchestrator
│           │   ├── analysis_PR.py          # PR analysis utilities
│           │   ├── batch_skill_extractor.py # Batch LLM skill extraction
│           │   ├── commit_history_utils.py  # Commit-to-skills mapping
│           │   ├── jira_agent.py           # Jira ticket skill analysis
│           │   ├── llm.py                  # LLM client (Groq + Gemini fallback)
│           │   ├── llm_rate_limiter.py     # Rate limiting for LLM calls
│           │   ├── multiset_engine.py      # Multi-signal ranking engine
│           │   ├── profile_cache.py        # Filesystem-based reviewer profile cache
│           │   ├── prompts.py              # LLM prompt templates
│           │   └── scorer_agent.py         # Candidate scoring agent
│           ├── Data/
│           │   ├── commit_diff_vectordb.py # Builds ChromaDB from commit diffs
│           │   ├── searching_into_vectordb.py  # Vector similarity search
│           │   ├── commit_vector_db/       # ChromaDB store (default embeddings)
│           │   └── commit_vector_db_nomic/ # ChromaDB store (Nomic embeddings)
│           └── requirements.txt
│
├── mock_run.py                     # End-to-end mock test runner
└── Readme.md
```

---

## Modules

### Risk Analysis

The risk module predicts how likely a pull request is to introduce a bug.

**Model:** Support Vector Machine (SVM) with probability calibration (`predict_proba`), also compared against a logistic regression baseline and a DistilBERT experiment.

**Dataset:** Apache JIT dataset — a well-known Just-In-Time defect prediction dataset covering real Apache project commits.

**Input features** (JIT metrics extracted by the .NET backend from GitHub):

| Feature  | Description                                      |
|----------|--------------------------------------------------|
| `la`     | Lines added                                      |
| `ld`     | Lines deleted                                    |
| `nf`     | Number of files modified                         |
| `nd`     | Number of directories modified                   |
| `ns`     | Number of subsystems modified                    |
| `ent`    | Change entropy (diffusion)                       |
| `ndev`   | Number of developers who touched these files     |
| `age`    | Average time since last change (days)            |
| `nuc`    | Number of unique last changes                    |
| `aexp`   | Author total experience (commits)                |
| `arexp`  | Author recent experience                         |
| `asexp`  | Author subsystem experience                      |

**Output:** `bug_probability` — a float in [0, 1] indicating the probability that the PR introduces a defect.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/predict` | Direct prediction from raw feature values |
| `GET`  | `/orchestrate/{owner}/{repo}/{pull_number}` | Fetches PR metrics from .NET backend and returns risk score |

---

### Reviewer Recommendation

The reviewer module matches a pull request with the most qualified reviewers on the team using a 5-stage pipeline.

#### Stage 1 — Skill Extraction
The raw `git diff` and PR metadata are fed to an LLM which identifies the specific technical competencies required to safely review the code (e.g., `React Hooks`, `PostgreSQL Migrations`, `JWT Auth`).

#### Stage 2 — Role Mapping via RAG
Extracted skills are mapped to organizational roles (e.g., Database Administrator, Security Engineer) by querying a ChromaDB vector database that stores role personas.

#### Stage 3 — Smart Caching & Commit Fetching
To avoid running LLM inference over every developer's full commit history on each request, the system uses a filesystem-based **ProfileCache**:
- **Cache hit** — loads the developer's skills from the local cache (0 LLM calls).
- **Cache miss** — fetches recent commits from GitHub, runs Ollama (`phi3:mini`) locally to extract skills, then saves the result to cache.

#### Stage 4 — Jira Context Analysis
The **Jira Agent** calls the .NET backend (`/api/Jira/assigned-tickets`) to fetch each candidate's recently assigned tickets, then uses an LLM to summarize their current active focus areas.

#### Stage 5 — Matchmaker Scoring
The **Scorer Agent** blends the following signals into a **0–100 confidence score**:
- **Tversky Similarity Index** — high-speed file-path overlap between the PR and the candidate's commit history.
- **Skill alignment** — match between extracted PR skills, cached developer skills, and Jira context.
- **Math fallback** — if LLM scoring fails, a pure mathematical fallback ensures the service never goes down.

#### Key components

| File | Responsibility |
|------|---------------|
| `Reviewer_Engine.py` | Main orchestrator — indexes contributors, checks cache, delegates scoring |
| `profile_cache.py` | Filesystem JSON cache for developer skill profiles |
| `scorer_agent.py` | Formats candidates into LLM prompts, returns score + justification |
| `multiset_engine.py` | Aggregates multiple ranking signals into a final ordered list |
| `commit_history_utils.py` | GitHub API client — fetches commits and maps them to skills |
| `jira_agent.py` | Interfaces with .NET Jira bridge to pull assigned tickets |
| `prompts.py` | Isolated LLM prompt templates |

#### LLM Stack

| Role | Model |
|------|-------|
| Primary LLM | Groq — `llama-3.3-70b-versatile` |
| Fallback LLM | Google Gemini |
| Local profiling | Ollama — `phi3:mini` |

#### Reviewer response format

Every recommended reviewer is returned with:

```json
{
  "name": "dev_username",
  "confidence_score": 92,
  "justification": "Has strong Python and FastAPI skills with high file-path overlap on modified modules."
}
```

- `confidence_score` — integer from 0 to 100.
- `justification` — human-readable explanation of why this reviewer was recommended.

#### Endpoints

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
| Primary LLM | Groq (`llama-3.3-70b-versatile`) |
| Fallback LLM | Google Gemini |
| Local LLM | Ollama (`phi3:mini`) |
| Vector DB | ChromaDB |
| Embeddings | Nomic, sentence-transformers |
| LLM Orchestration | LangChain |
| Data Storage | PostgreSQL, Redis (profile cache) |
| DevOps | Docker, GitHub Actions |

---

## Integrations

| Platform | Purpose |
|----------|---------|
| **GitHub** | Fetch PR metadata, file diffs, commit history, developer experience |
| **GitLab** | Same as GitHub for GitLab-hosted repositories |
| **Jira** | Extract assigned ticket context to enrich reviewer skill profiles |

---

## API Reference

### Risk API — `http://localhost:8000`

#### `POST /predict`

Direct prediction from raw JIT feature values.

**Request:**
```json
{
  "la": 120, "ld": 30, "nf": 5, "nd": 2,
  "ns": 1, "ent": 0.85, "ndev": 3,
  "age": 90.0, "nuc": 4, "aexp": 200,
  "arexp": 50, "asexp": 10
}
```

**Response:**
```json
{
  "bug_probability": 0.73
}
```

#### `GET /orchestrate/{owner}/{repo}/{pull_number}`

Fetches all PR metrics from the .NET backend automatically and returns the risk score.

---

### Reviewer Recommender API — `http://localhost:8001`

#### `POST /api/recommend-reviewers`

**Request:**
```json
{
  "owner": "org-name",
  "repo": "repo-name",
  "pr_number": 42,
  "required_reviewers": [
    {
      "username": "dev_username",
      "jira_username": "Dev Name",
      "raw_skills": ["python", "fastapi"]
    }
  ],
  "options": {
    "top_k": 5,
    "prioritize_recent_activity": true,
    "commits_per_reviewer": 50
  },
  "jira_token": "YOUR_JIRA_ACCESS_TOKEN",
  "jira_cloud_id": "your-cloud-id",
  "jira_project_key": "SCRUM"
}
```

**Response:**
```json
{
  "recommended_reviewers": [
    {
      "name": "dev_username",
      "confidence_score": 92,
      "justification": "Has explicit Python skills and high file-path similarity..."
    }
  ]
}
```

#### `POST /api/orchestrator`

Profiles a provided list of users and ranks them for a specific PR.

**Request:**
```json
{
  "owner": "org-name",
  "repo": "repo-name",
  "pr_number": 42,
  "users": [
    {
      "github_username": "dev_username",
      "jira_username": "Dev Name",
      "jira_token": "YOUR_JIRA_ACCESS_TOKEN",
      "jira_cloud_id": "your-cloud-id",
      "jira_project_key": "SCRUM",
      "raw_skills": ["python", "react", "fastapi"]
    }
  ],
  "commits_per_user": 50,
  "options": {
    "top_k": 5,
    "prioritize_recent_activity": true
  }
}
```

**Response:**
```json
{
  "recommended_reviewers": [
    {
      "name": "dev_username",
      "confidence_score": 88,
      "justification": "Matched based on raw_skills override and dynamic profiling..."
    }
  ]
}
```

### .NET Backend — `http://localhost:5051/api/GitHubAuth`

Provides PR metrics, commit history, file lists, and developer experience data consumed by both Python APIs.

---

## Testing & Evaluation

Run the unit tests and evaluation metrics:

```bash
cd CodienceProject
python -m codience.src.test_and_evaluate
```

The test suite covers:

- **Unit tests** — FastAPI endpoint tests using `TestClient` with mocked dependencies.
- **Evaluation metrics** — measures recommendation quality against ground-truth reviewer data:

| Metric | Description |
|--------|-------------|
| **MRR** (Mean Reciprocal Rank) | Average rank position of the first correct recommendation |
| **Hit Rate@k** | Fraction of PRs where at least one correct reviewer appears in top-k |
| **Precision@k** | Fraction of top-k recommendations that are correct |
| **Recall@k** | Fraction of actual reviewers captured in top-k |

---

## Setup & Installation

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
GROQ_API_KEY=...
```

---

## Mentorship

| Role | Name |
|------|------|
| Academic Supervisor | Dr. Mohamed El Ramly |
| Teaching Assistant | Hager Mahmoud |

---

*Codeians — built by the Sudonators team.*
