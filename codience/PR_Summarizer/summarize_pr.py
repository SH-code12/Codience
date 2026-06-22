import re
import sys

from llm import get_model
from prompts import (
    PR_SUMMARY_PROMPT,
    CHUNK_SUMMARY_PROMPT,
    REDUCE_SUMMARY_PROMPT,
)

# Same Gemini model the Reviewer Recommender uses, so both features stay aligned.
MODEL = "gemini-3.1-flash-lite-preview"

# Option A vs B routing: diffs at or below this size are sent whole in one call
# (best coherence). Larger diffs fall back to per-file map-reduce. ~200k chars is
# roughly ~50k tokens, comfortably inside the Gemini flash context window.
SINGLE_CALL_CHAR_LIMIT = 200_000

# In map-reduce mode, the maximum chars per chunk sent to the model.
CHUNK_CHAR_LIMIT = 60_000


def _log(message: str):
    print(message, file=sys.stderr)


def _generate(client, prompt: str) -> str:
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return (response.text or "").strip()


def _split_diff_by_file(diff: str) -> list:
    """Split a git diff into per-file sections, keeping each `diff --git` header.
    Any section larger than CHUNK_CHAR_LIMIT is hard-split by size. Non-git diffs
    fall back to fixed-size chunks."""
    sections = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)
    sections = [s for s in sections if s.strip()]
    if not sections:  # not a git-style diff
        sections = [diff]

    chunks = []
    for section in sections:
        if len(section) <= CHUNK_CHAR_LIMIT:
            chunks.append(section)
        else:
            for i in range(0, len(section), CHUNK_CHAR_LIMIT):
                chunks.append(section[i:i + CHUNK_CHAR_LIMIT])
    return chunks


def _summarize_single(client, pr_data: dict, diff: str) -> str:
    """Option A: send the entire diff in one call."""
    prompt = PR_SUMMARY_PROMPT.format(
        title=pr_data.get("title", "N/A"),
        description=pr_data.get("description", "N/A"),
        diff=diff,
    )
    return _generate(client, prompt)


def _summarize_mapreduce(client, pr_data: dict, diff: str) -> str:
    """Option B: summarize each file section, then combine into one summary."""
    chunks = _split_diff_by_file(diff)
    _log(f"Large diff ({len(diff)} chars): map-reduce over {len(chunks)} chunks.")

    notes = []
    for chunk in chunks:
        note = _generate(client, CHUNK_SUMMARY_PROMPT.format(
            title=pr_data.get("title", "N/A"),
            chunk=chunk,
        ))
        if note:
            notes.append(note)

    if not notes:
        return ""

    return _generate(client, REDUCE_SUMMARY_PROMPT.format(
        title=pr_data.get("title", "N/A"),
        description=pr_data.get("description", "N/A"),
        file_notes="\n\n".join(notes),
    ))


def summarize_pr(pr_data: dict) -> str:
    """Produce a concise markdown summary of what happened in a pull request.

    pr_data is shaped like the data the .NET backend provides:
        {"title": str, "description": str, "diff": str}

    The full diff is sent in a single call when it fits (Option A); very large
    diffs fall back to per-file map-reduce (Option B). On failure, returns a safe
    fallback message.
    """
    diff = pr_data.get("diff", "") or ""

    try:
        # Inside the try so a missing/invalid GEMINI_API_KEY (which raises at
        # client construction) returns a safe fallback instead of a 500.
        client = get_model()
        if len(diff) <= SINGLE_CALL_CHAR_LIMIT:
            summary = _summarize_single(client, pr_data, diff)
        else:
            summary = _summarize_mapreduce(client, pr_data, diff)

        if not summary:
            _log("Warning: LLM returned an empty summary.")
            return "Summary unavailable: the model returned no content."
        return summary
    except Exception as e:
        _log(f"Error generating PR summary: {e}")
        return "Summary unavailable due to an internal error."
