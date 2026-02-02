"""Persistent two-layer cache: in-memory LRU (L1) + PostgreSQL (L2).

No TTL expiration. Entries persist until explicitly invalidated.
L1 provides fast access; L2 survives server restarts.
"""

import hashlib
import json
import logging
import pickle
import threading
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


def _get_session():
    """Lazy import to avoid circular dependency at module load time."""
    from backend.config import SessionLocal
    return SessionLocal()


class PersistentCache:
    """Thread-safe cache with in-memory LRU (L1) backed by PostgreSQL (L2).

    - get(): check L1 → L2 → None
    - set(): write to L1 and L2
    - clear(): wipe both layers for this namespace
    - No TTL — entries live until explicitly cleared
    - max_size bounds L1 only; L2 is unbounded (cleared on invalidation)
    """

    def __init__(self, namespace: str, max_size: int):
        self._namespace = namespace
        self._max_size = max_size
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        # L1 check
        with self._lock:
            value = self._store.get(key)
            if value is not None:
                self._store.move_to_end(key)
                return value

        # L2 check
        try:
            from backend.models.governance import CacheEntry
            db = _get_session()
            try:
                row = db.query(CacheEntry).filter_by(
                    namespace=self._namespace, cache_key=key,
                ).first()
                if row is None:
                    return None
                value = pickle.loads(row.value)
                # Promote to L1
                with self._lock:
                    self._store[key] = value
                    self._store.move_to_end(key)
                    while len(self._store) > self._max_size:
                        self._store.popitem(last=False)
                return value
            except (pickle.UnpicklingError, Exception) as e:
                # Stale/corrupt entry — delete it and treat as miss
                if isinstance(e, pickle.UnpicklingError):
                    logger.warning("Cache L2 unpickle failed for %s/%s, deleting stale entry", self._namespace, key[:12])
                    try:
                        db.query(CacheEntry).filter_by(
                            namespace=self._namespace, cache_key=key,
                        ).delete()
                        db.commit()
                    except Exception:
                        db.rollback()
                    return None
                logger.debug("Cache L2 read error for %s: %s", self._namespace, e)
                return None
            finally:
                db.close()
        except Exception as e:
            logger.debug("Cache L2 unavailable for %s: %s", self._namespace, e)
            return None

    def set(self, key: str, value: Any) -> None:
        # L1 write
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

        # L2 write
        try:
            from backend.models.governance import CacheEntry
            blob = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            db = _get_session()
            try:
                existing = db.query(CacheEntry).filter_by(
                    namespace=self._namespace, cache_key=key,
                ).first()
                if existing:
                    existing.value = blob
                else:
                    db.add(CacheEntry(
                        namespace=self._namespace,
                        cache_key=key,
                        value=blob,
                    ))
                db.commit()
            except Exception as e:
                db.rollback()
                logger.debug("Cache L2 write error for %s: %s", self._namespace, e)
            finally:
                db.close()
        except Exception as e:
            logger.debug("Cache L2 unavailable for %s: %s", self._namespace, e)

    def clear(self) -> None:
        # L1 clear
        with self._lock:
            self._store.clear()

        # L2 clear
        try:
            from backend.models.governance import CacheEntry
            db = _get_session()
            try:
                db.query(CacheEntry).filter_by(namespace=self._namespace).delete()
                db.commit()
                logger.debug("Cache L2 cleared for namespace %s", self._namespace)
            except Exception as e:
                db.rollback()
                logger.debug("Cache L2 clear error for %s: %s", self._namespace, e)
            finally:
                db.close()
        except Exception as e:
            logger.debug("Cache L2 unavailable for clear on %s: %s", self._namespace, e)

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


def cache_key(*args, **kwargs) -> str:
    """Build a deterministic cache key from positional and keyword arguments."""
    raw = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Singleton cache instances ────────────────────────────────────────────────
dashboard_cache = PersistentCache(namespace="dashboard", max_size=200)
sql_tool_cache = PersistentCache(namespace="sql_tool", max_size=500)
llm_cache = PersistentCache(namespace="llm", max_size=100)
query_results_cache = PersistentCache(namespace="query_results", max_size=500)


def invalidate_all() -> None:
    """Clear dashboard and sql_tool caches — call after investigation completes.

    LLM cache is NOT cleared: prompts are deterministic (temperature=0) and
    the cache key includes the full prompt text, so if underlying data changes
    the prompts change too, producing different keys automatically.

    query_results_cache is NOT cleared: it holds investigation results that
    the WebSocket/status endpoints need for completed queries.
    """
    dashboard_cache.clear()
    sql_tool_cache.clear()
    logger.info("Caches invalidated (dashboard, sql_tool)")
