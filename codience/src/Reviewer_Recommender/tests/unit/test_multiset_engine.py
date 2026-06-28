import pytest
from datetime import datetime, timezone, timedelta
from collections import Counter
from PRNew.multiset_engine import (
    tokenise_path,
    commit_multiset,
    extinguish,
    build_reviewer_profile,
    tversky_similarity,
    jaccard_similarity,
    score_reviewer
)

def test_tokenise_path():
    assert tokenise_path("src/main/java/package1/SomeClass.java") == ["src", "main", "java", "package1", "someclass", "java"]
    assert tokenise_path("path-with-dashes/and_underscores.txt") == ["path", "with", "dashes", "and", "underscores", "txt"]
    assert tokenise_path("CamelCaseIsNotSplit/file.ts") == ["camelcaseisnotsplit", "file", "ts"]

def test_commit_multiset():
    paths = ["src/file1.py", "src/file2.py"]
    result = commit_multiset(paths)
    assert result == Counter({"src": 2, "file1": 1, "py": 2, "file2": 1})

def test_extinguish():
    assert extinguish(0) == 1.0
    assert extinguish(180, decay_factor=2.0, halflife_days=180) == 0.5
    assert extinguish(360, decay_factor=2.0, halflife_days=180) == 0.25

def test_build_reviewer_profile_no_decay():
    commits = [
        {"files": ["src/main.py", "src/utils.py"]},
        {"files": ["src/main.py"]}
    ]
    profile = build_reviewer_profile(commits, use_decay=False)
    assert profile == Counter({"src": 3, "main": 2, "py": 3, "utils": 1})

def test_build_reviewer_profile_with_decay():
    ref_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    # Commit 1 is exactly 180 days old (halflife = 180, factor = 2.0 -> multiplier 0.5)
    date_180_days_ago = (ref_date - timedelta(days=180)).isoformat()
    # Commit 2 is today (0 days old -> multiplier 1.0)
    date_today = ref_date.isoformat()
    
    commits = [
        {"files": ["src/old.py"], "date": date_180_days_ago},
        {"files": ["src/new.py"], "date": date_today}
    ]
    profile = build_reviewer_profile(
        commits, use_decay=True, decay_factor=2.0, halflife_days=180, reference_date=ref_date
    )
    # old.py elements get multiplied by 0.5
    # new.py elements get multiplied by 1.0
    assert profile["src"] == 1.5  # 0.5 from old, 1.0 from new
    assert profile["old"] == 0.5
    assert profile["new"] == 1.0
    assert profile["py"] == 1.5

def test_tversky_similarity():
    profile = Counter({"src": 2, "file1": 1})
    commit = Counter({"src": 1, "file2": 1})
    
    # Inter: "src": min(2,1) = 1
    # p_only: "src": max(0, 2-1)=1, "file1": max(0, 1-0)=1 -> total p_only = 2
    # c_only: "src": max(0, 1-2)=0, "file2": max(0, 1-0)=1 -> total c_only = 1
    # denom (alpha=0.5, beta=0.5) = 1 + 0.5*2 + 0.5*1 = 1 + 1 + 0.5 = 2.5
    # score = 1 / 2.5 = 0.4
    
    score = tversky_similarity(profile, commit, alpha=0.5, beta=0.5)
    assert score == 0.4
    
    # Empty cases
    assert tversky_similarity(Counter(), commit) == 0.0
    assert tversky_similarity(profile, Counter()) == 0.0

def test_jaccard_similarity():
    profile = Counter({"src": 2, "file1": 1})
    commit = Counter({"src": 1, "file2": 1})
    
    # Inter = 1
    # Union = sum(profile+commit) - Inter = (2+1+1+1) - 1 = 4
    # score = 1 / 4 = 0.25
    score = jaccard_similarity(profile, commit)
    assert score == 0.25

def test_score_reviewer():
    commits = [
        {"files": ["src/main.py"], "date": datetime.now(timezone.utc).isoformat()}
    ]
    pr_files = ["src/main.py"]
    
    res = score_reviewer(commits, pr_files, use_decay=False)
    # Profile = {"src":1, "main":1, "py":1}
    # Commit = {"src":1, "main":1, "py":1}
    # Both identical, scores should be 1.0
    assert res["tversky"] == 1.0
    assert res["jaccard"] == 1.0
    assert res["profile_size"] == 3
    assert res["commit_size"] == 3
