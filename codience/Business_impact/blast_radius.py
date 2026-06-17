"""
blast_radius.py
───────────────
Measures how many parts of the codebase are affected by the changed files.

Research basis:
  - Springer/EMSE 2024: "call-graph-based dependency analysis ... to calculate
    per-file risk scores" → we proxy call-graph depth with import reference counting.
  - CodePlan / MS Research 2023: ranking diff hunks by "graph properties" (in-degree
    of changed node in the dependency graph) rather than raw line count.
"""

import re
from models import BlastRadiusDetail

# ── Critical-path module patterns ──────────────────────────────────────────────
CRITICAL_PATH_RE = [
    r"payment|billing|checkout|invoice|stripe|paypal|transaction",
    r"auth|oauth|jwt|session|login|logout|password|credential|token",
    r"database|db|migration|schema|orm|repository",
    r"(api|web).*(controller|router|handler|endpoint|view|route)",
    r"middleware|gateway|proxy|interceptor",
    r"user|account|profile|identity",
    r"email|notification|webhook",
    r"queue|worker|job|scheduler|cron",
    r"config|settings|environment|secrets",
]

CODE_EXTENSIONS = {
    ".py", ".ts", ".js", ".cs", ".java", ".go", ".rb", ".php", 
    ".kt", ".swift", ".rs", ".cpp", ".c", ".tsx", ".jsx"
}

ROUTE_PATTERNS = [
    r'@(app|router|bp)\.(get|post|put|patch|delete)\s*\(',
    r'@(Get|Post|Put|Patch|Delete|HttpGet|HttpPost|HttpPut)',
    r'\[Http(Get|Post|Put|Delete|Patch)\]',
    r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)',
    r'(get|post|put|patch|delete)\s+[\'\"]/[\w/{}]',
    r'router\.(get|post|put|delete)\s*\(',
]

def _code_files(files: list[str]) -> list[str]:
    return [f for f in files if any(f.endswith(e) for e in CODE_EXTENSIONS)]

def _critical_files(files: list[str]) -> list[str]:
    out = []
    for f in files:
        lower = f.lower()
        if any(re.search(p, lower) for p in CRITICAL_PATH_RE):
            out.append(f)
    return out

def _count_routes(diff: str) -> int:
    n = 0
    for p in ROUTE_PATTERNS:
        n += len(re.findall(p, diff, re.IGNORECASE))
    return n

def _count_import_refs(code_files: list[str], diff: str) -> int:
    stems = set()
    for f in code_files:
        stem = re.sub(r"\.(py|ts|js|cs|java|go|rb|php|kt|swift|rs|tsx|jsx)$", "", f.split("/")[-1])
        if len(stem) > 3:
            stems.add(stem.lower())

    refs = 0
    body = "\n".join(
        l[1:] for l in diff.split("\n")
        if l.startswith("+") or l.startswith(" ")
    ).lower()

    for stem in stems:
        pat = rf"(import|require|from|using|include)\s+.*{re.escape(stem)}"
        refs += len(re.findall(pat, body))

    return min(refs, 60)

def score_blast_radius(changed_files: list[str], diff: str) -> BlastRadiusDetail:
    code = _code_files(changed_files)
    critical = _critical_files(code)

    callers = _count_import_refs(code, diff)
    routes = _count_routes(diff)
    n_crit = len(critical)

    caller_c = min(callers / 10.0, 1.0) * 0.40
    route_c = min(routes / 3.0, 1.0) * 0.25
    crit_c = min(n_crit * 0.15, 0.60) * 0.35

    score = round(min(caller_c + route_c + crit_c, 1.0), 4)

    parts = []
    if callers:
        parts.append(f"{callers} import ref(s) to changed modules")
    if routes:
        parts.append(f"{routes} API route declaration(s) modified")
    if critical:
        parts.append(f"critical-path files: {', '.join(critical[:3])}")

    return BlastRadiusDetail(
        internal_callers=callers,
        external_api_routes=routes,
        critical_files_hit=n_crit,
        score=score,
        explanation="; ".join(parts) or "No significant blast-radius signals",
    )