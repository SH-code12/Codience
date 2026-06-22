PR_SUMMARY_PROMPT = """
You are a Senior Software Engineer reviewing a pull request. Your task is to
explain, clearly and concisely, what happened in this pull request so a teammate
can understand it at a glance without reading the full diff.

PR DATA:
Title: {title}
Description: {description}
Code Changes (Diff):
{diff}

INSTRUCTIONS:
1. Focus on WHAT changed and WHY it matters, not a line-by-line readout of the diff.
2. Be factual and grounded in the data provided. Do not invent changes that are
   not present in the title, description, or diff.
3. Keep it short and skimmable.

OUTPUT FORMAT (Markdown only, no JSON, no code fences around the whole answer):
A single-sentence **Overview** of the change.

**Key changes**
- bullet points of the most important changes (3-6 bullets)

**Impact** (optional, one or two lines): notable effects, risks, or areas a
reviewer should pay attention to. Omit this section if there is nothing notable.
"""


# --- Map-reduce prompts (used only for very large diffs) ---

# MAP step: summarize one section (usually one file) of a large diff into terse notes.
CHUNK_SUMMARY_PROMPT = """
You are a Senior Software Engineer. Below is one portion of the code changes
(one or more files) from a pull request titled "{title}". Summarize what changed
in THIS portion only.

CODE CHANGES:
{chunk}

INSTRUCTIONS:
- Be factual and specific; do not invent changes that are not present.
- Output 1-5 short markdown bullet points. No preamble, no headings.
"""

# REDUCE step: combine the per-section notes into the final PR summary.
REDUCE_SUMMARY_PROMPT = """
You are a Senior Software Engineer. You are given a pull request's title and
description, plus per-section notes describing what changed across its files.
Write a single concise summary of what happened in the WHOLE pull request.

Title: {title}
Description: {description}

PER-SECTION NOTES:
{file_notes}

INSTRUCTIONS:
1. Synthesize across all notes; group related changes. Do not just concatenate them.
2. Be factual and grounded in the notes. Do not invent changes.
3. Keep it short and skimmable.

OUTPUT FORMAT (Markdown only, no JSON, no code fences around the whole answer):
A single-sentence **Overview** of the change.

**Key changes**
- bullet points of the most important changes (3-6 bullets)

**Impact** (optional, one or two lines): notable effects, risks, or areas a
reviewer should pay attention to. Omit this section if there is nothing notable.
"""
