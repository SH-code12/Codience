# Codience — Pull Request Business Impact Scorer Engine

The **Business Impact Scorer** is an asynchronous, multi-signal AI engine designed to evaluate the systemic risk, architectural exposure, and scheduling urgency of incoming pull requests. 

By blending classical static analysis heuristics (dependency graph analysis, route parsing) with semantic evaluation powered by a secure, local Large Language Model (**Qwen2.5-Coder:1.5b**), the engine calculates a unified score ($0\text{–}100$) to help engineering managers prioritize reviews and prevent critical path regressions.

---

## 🛠️ System Architecture & Data Flow

The microservice acts as a secure analysis bridge connecting your `.NET API Core Controller`, the GitHub REST API, and Jira instances. 



1. **Ingress & Fetch:** The `.NET Backend` triggers a score request or FastAPI directly pulls an open PR from GitHub.
2. **Identity Resolution:** The engine extracts live authenticated developer profile context using secure token network lookups to map GitHub handles to corporate identities.
3. **Multi-Signal Extraction:**
   - **Blast Radius:** Parses file extensions, tracks recursive module call structures, and evaluates API route impacts.
   - **User Exposure:** Correlates PR text changes with matched severity levels and live customer counts from linked Jira tickets using log-scaled calculations.
   - **Deadline Pressure:** Tracks proximity to sprint milestones via a directional sigmoid penalty curve.
4. **Local AI Inference Engine:** Diffs and ticket schemas are pushed to a completely local Ollama instance running `qwen2.5-coder:1.5b` to assess functional systemic risks and isolate affected downstream applications.
5. **Score Aggregation:** Merges empirical rules ($42\%$) and LLM semantics ($58\%$) into a standardized risk report.

---

## 📊 Core Scoring Methodology

The final risk profile maps to a $0\text{–}100$ scale across three priority bands:
* 🔴 **HIGH (Score $\ge 70$):** Demands immediate verification. Automated enforcement forces `should_block_merge=True` for scores $\ge 80$.
* 🟡 **MEDIUM (Score $40\text{–}69$):** Standard review path. Requires 2 peer review sign-offs.
* 🟢 **LOW (Score $< 40$):** Minor operational noise, documentation, or isolated refactors.

### Mathematical Formulations

#### 1. Blast Radius Risk Assessment
Approximates dependency depth over a call-graph approximation using an index decay structure up to $k=3$ hops:

$$BR(f) = \sum_{d=1}^{k} \frac{1}{d} \cdot \text{dependencies}(f,d)$$

The absolute weight structure guarantees strict balance across four key vectors so that individual import additions do not oversaturate risk profiles:
* Internal Module Ref Caller Capacity ($30\%$)
* API Endpoints Modified ($20\%$)
* Critical Code Paths Breached ($25\%$)
* Graph Dependency Density ($25\%$)

#### 2. User Exposure Index
Calculates potential blast exposure by weighting customer counts ($Users$), ticket structural severities ($Sev$), and explicit revenue flags ($Rev$):

$$\text{UI}_{\text{raw}} = \alpha \cdot \ln(1 + \text{Users}) + \beta \cdot \text{Sev} + \gamma \cdot \text{Rev}$$

*Where $\alpha=0.5, \beta=0.3, \gamma=0.2$. Normalized continuously using an adjusted scale divisor.*

#### 3. Deadline Pressure Curve
Maps delivery pressure relative to the nearest sprint deadline using an asymmetric sigmoid curve. It avoids clamping overdue tickets to zero so that overdue PRs ($\text{Days} < 0$) reflect a progressive urgency boost:

$$\text{DP} = \frac{1}{1 + e^{k \cdot \text{Days}}} \quad (k=0.15)$$

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* Ollama running locally (`ollama serve`)
* Downloaded Model: `ollama pull qwen2.5-coder:1.5b`

### Run Main Appp 
    uvicorn main:app --host 127.0.0.1 --port 8003 --reload

#### Open Swigger 
    http://localhost:8003/docs