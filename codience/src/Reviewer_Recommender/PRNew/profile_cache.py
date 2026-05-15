"""
profile_cache.py
────────────────
Two-layer cache designed to avoid rebuilding reviewer profiles and
recomputing similarity scores for every PR request.

Layer 1 (L1) — in-process Python dict with TTL.
    Fast, zero-latency.  Lost on restart.  Best for same-process repeated calls.

Layer 2 (L2) — pluggable backend (Redis or disk JSON).
    Survives restarts.  Controlled by CACHE_BACKEND env var:
      "redis"   → requires redis-py; REDIS_URL env var (default localhost:6379)
      "disk"    → JSON files under CACHE_DIR (default /tmp/reviewer_cache)
      "none"    → L2 disabled (L1 only)

Cache keys
──────────
  profile:{repo}:{author}:{decay_hash}   → serialised Counter (json)
  similarity:{repo}:{author}:{pr_hash}   → float similarity score

TTL defaults (all overridable via env)
  CACHE_PROFILE_TTL_SEC   = 3600    (1 hour — profiles are stable)
  CACHE_SIMILARITY_TTL_SEC = 300    (5 min  — PR hash changes rarely mid-review)

Usage
─────
  from profile_cache import ProfileCache

  cache = ProfileCache()                        # uses env config
  cache.set_profile("myrepo", "alice", counter) # store
  p = cache.get_profile("myrepo", "alice")      # retrieve or None
  cache.invalidate_author("myrepo", "alice")    # force rebuild on next call
"""

import json
import os
import time
import hashlib
from collections import Counter
from pathlib import Path
from typing import Optional

# ── Config from environment ────────────────────────────────────────────────────

CACHE_BACKEND             = os.getenv("CACHE_BACKEND", "disk").lower()
REDIS_URL                 = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_DIR                 = Path(os.getenv("CACHE_DIR", "/tmp/reviewer_cache"))
CACHE_PROFILE_TTL         = int(os.getenv("CACHE_PROFILE_TTL_SEC", "3600"))
CACHE_SIMILARITY_TTL      = int(os.getenv("CACHE_SIMILARITY_TTL_SEC", "300"))


# ── L1: in-process TTL store ───────────────────────────────────────────────────

class _L1Store:
    """Simple in-memory dict with per-entry expiry."""

    def __init__(self):
        self._store: dict[str, tuple[object, float]] = {}   # key → (value, expires_at)

    def get(self, key: str) -> Optional[object]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: object, ttl: int) -> None:
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]

    def clear(self) -> None:
        self._store.clear()


# ── L2 backend implementations ─────────────────────────────────────────────────

class _DiskBackend:
    """Stores cache entries as JSON files under CACHE_DIR."""

    def __init__(self, base_dir: Path = CACHE_DIR):
        self.base = base_dir
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = hashlib.sha1(key.encode()).hexdigest()
        return self.base / f"{safe}.json"

    def get(self, key: str) -> Optional[object]:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
            if time.time() > data["expires_at"]:
                p.unlink(missing_ok=True)
                return None
            return data["value"]
        except Exception:
            return None

    def set(self, key: str, value: object, ttl: int) -> None:
        try:
            self._path(key).write_text(json.dumps({
                "key": key,
                "value": value,
                "expires_at": time.time() + ttl,
            }))
        except Exception as exc:
            print(f"⚠️  Cache write failed [{key}]: {exc}")

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def delete_prefix(self, prefix: str) -> None:
        # Disk backend can't efficiently scan by prefix — iterate all files
        for p in self.base.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                if data.get("key", "").startswith(prefix):
                    p.unlink(missing_ok=True)
            except Exception:
                continue


class _RedisBackend:
    """Redis-backed L2 store. Falls back to no-op if redis-py is missing."""

    def __init__(self, url: str = REDIS_URL):
        try:
            import redis
            self._r = redis.from_url(url, decode_responses=True)
            self._r.ping()
            self._ok = True
        except Exception as exc:
            print(f"⚠️  Redis unavailable ({exc}). L2 cache disabled.")
            self._ok = False

    def get(self, key: str) -> Optional[object]:
        if not self._ok:
            return None
        try:
            raw = self._r.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def set(self, key: str, value: object, ttl: int) -> None:
        if not self._ok:
            return
        try:
            self._r.setex(key, ttl, json.dumps(value))
        except Exception as exc:
            print(f"⚠️  Redis write failed [{key}]: {exc}")

    def delete(self, key: str) -> None:
        if not self._ok:
            return
        try:
            self._r.delete(key)
        except Exception:
            pass

    def delete_prefix(self, prefix: str) -> None:
        if not self._ok:
            return
        try:
            keys = self._r.keys(f"{prefix}*")
            if keys:
                self._r.delete(*keys)
        except Exception:
            pass


class _NullBackend:
    def get(self, key): return None
    def set(self, key, value, ttl): pass
    def delete(self, key): pass
    def delete_prefix(self, prefix): pass


def _build_l2() -> object:
    if CACHE_BACKEND == "redis":
        return _RedisBackend()
    if CACHE_BACKEND == "disk":
        return _DiskBackend()
    return _NullBackend()


# ── Serialisation helpers for Counter ─────────────────────────────────────────

def _counter_to_json(c: Counter) -> dict:
    return {k: v for k, v in c.items()}


def _json_to_counter(d: Optional[dict]) -> Optional[Counter]:
    if d is None:
        return None
    return Counter({k: float(v) for k, v in d.items()})


# ── Public cache interface ─────────────────────────────────────────────────────

class ProfileCache:
    """
    Two-layer cache (L1 memory + L2 disk/Redis) for reviewer profiles
    and similarity scores.

    Thread-safe for reads.  Writes have no lock (last-write-wins; acceptable
    since profiles are deterministic given the same input commits).
    """

    def __init__(
        self,
        profile_ttl:    int = CACHE_PROFILE_TTL,
        similarity_ttl: int = CACHE_SIMILARITY_TTL,
    ):
        self._l1 = _L1Store()
        self._l2 = _build_l2()
        self.profile_ttl    = profile_ttl
        self.similarity_ttl = similarity_ttl

    # ── Profile cache ──────────────────────────────────────────────────────────

    def _profile_key(self, repo: str, author: str, decay_tag: str = "") -> str:
        return f"profile:{repo}:{author}:{decay_tag}"

    def get_profile(self, repo: str, author: str, decay_tag: str = "") -> Optional[Counter]:
        key = self._profile_key(repo, author, decay_tag)

        # L1
        hit = self._l1.get(key)
        if hit is not None:
            return _json_to_counter(hit)

        # L2
        raw = self._l2.get(key)
        if raw is not None:
            counter = _json_to_counter(raw)
            if counter is not None:
                self._l1.set(key, raw, self.profile_ttl)   # warm L1
            return counter

        return None

    def set_profile(
        self,
        repo:      str,
        author:    str,
        profile:   Counter,
        decay_tag: str = "",
    ) -> None:
        key      = self._profile_key(repo, author, decay_tag)
        as_json  = _counter_to_json(profile)
        self._l1.set(key, as_json, self.profile_ttl)
        self._l2.set(key, as_json, self.profile_ttl)

    def invalidate_author(self, repo: str, author: str) -> None:
        """Force profile rebuild for this author on next request."""
        prefix = f"profile:{repo}:{author}:"
        self._l1.delete_prefix(prefix)
        self._l2.delete_prefix(prefix)

    # ── Similarity score cache ─────────────────────────────────────────────────

    def _sim_key(self, repo: str, author: str, pr_hash: str) -> str:
        return f"similarity:{repo}:{author}:{pr_hash}"

    def get_similarity(self, repo: str, author: str, pr_hash: str) -> Optional[float]:
        key = self._sim_key(repo, author, pr_hash)
        hit = self._l1.get(key)
        if hit is not None:
            return float(hit)
        raw = self._l2.get(key)
        if raw is not None:
            self._l1.set(key, raw, self.similarity_ttl)
            return float(raw)
        return None

    def set_similarity(
        self, repo: str, author: str, pr_hash: str, score: float
    ) -> None:
        key = self._sim_key(repo, author, pr_hash)
        self._l1.set(key, score, self.similarity_ttl)
        self._l2.set(key, score, self.similarity_ttl)

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def hash_pr(file_paths: list[str]) -> str:
        """Stable hash of a PR's changed files — used as cache key segment."""
        normalised = sorted(p.strip().lower() for p in file_paths)
        content    = "\n".join(normalised).encode()
        return hashlib.sha256(content).hexdigest()[:16]

    @staticmethod
    def decay_tag(decay_factor: float, halflife_days: float) -> str:
        return f"f{decay_factor}_l{halflife_days}"

    def clear_all(self) -> None:
        self._l1.clear()