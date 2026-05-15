"""
LLM Rate Limiter with Token Bucket Algorithm
Supports multiple models (Llama, Gemini, Groq) with per-model rate limits
"""

import time
import threading
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

class TokenBucket:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: float, capacity: int):
        """
        rate: tokens per second
        capacity: maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens, return True if successful"""
        with self.lock:
            now = time.time()
            # Refill tokens based on time elapsed
            elapsed = now - self.last_refill
            refill = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + refill)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_for_tokens(self, tokens: int = 1, timeout: float = None) -> bool:
        """Wait until tokens are available"""
        start = time.time()
        while not self.consume(tokens):
            if timeout and (time.time() - start) > timeout:
                return False
            time.sleep(0.1)
        return True


class LLMRateLimiter:
    """Rate limiter for multiple LLM providers"""
    
    # Rate limits per provider (tokens per second, burst capacity)
    # Adjust based on your API limits
# Rate limits per provider (tokens per second, burst capacity)
# More permissive for production
    PROVIDER_LIMITS = {
        "groq": {"rate": 0.5, "capacity": 10},     # 0.5 req/sec (30 per min) - Groq free tier
        "gemini": {"rate": 0.25, "capacity": 5},   # 0.25 req/sec (15 per min) - Gemini free tier
    }
    
    # Purpose-based cost (how many tokens consumed per call)
    PURPOSE_COST = {
        "pr_file_summary": 1,
        "pr_skill_extraction": 2,
        "candidate_scoring": 3,
        "history_summary": 2,
        "general": 1,
    }
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.buckets = {}
        self.stats = defaultdict(lambda: {"total": 0, "rate_limited": 0, "last_call": 0})
    
    def _get_bucket(self, provider: str) -> TokenBucket:
        if provider not in self.buckets:
            limits = self.PROVIDER_LIMITS.get(provider, {"rate": 1.0, "capacity": 5})
            self.buckets[provider] = TokenBucket(limits["rate"], limits["capacity"])
        return self.buckets[provider]
    
    def acquire(self, provider: str, purpose: str = "general", timeout: float = 30.0) -> bool:
        """Acquire permission to make an LLM call"""
        bucket = self._get_bucket(provider)
        cost = self.PURPOSE_COST.get(purpose, 1)
        
        self.stats[provider]["total"] += 1
        success = bucket.wait_for_tokens(cost, timeout)
        
        if success:
            self.stats[provider]["last_call"] = time.time()
        else:
            self.stats[provider]["rate_limited"] += 1
            print(f"⚠️ Rate limit exceeded for {provider} (purpose: {purpose})")
        
        return success
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            provider: {
                "total_calls": stats["total"],
                "rate_limited": stats["rate_limited"],
                "success_rate": f"{(stats['total'] - stats['rate_limited']) / max(stats['total'], 1) * 100:.1f}%"
            }
            for provider, stats in self.stats.items()
        }
    
    def print_stats(self):
        """Print rate limiter statistics"""
        print("\n" + "="*50)
        print("LLM RATE LIMITER STATISTICS")
        print("="*50)
        for provider, stats in self.get_stats().items():
            print(f"{provider.upper()}:")
            print(f"  Total calls: {stats['total_calls']}")
            print(f"  Rate limited: {stats['rate_limited']}")
            print(f"  Success rate: {stats['success_rate']}")
        print("="*50)


# Global instance
rate_limiter = LLMRateLimiter()