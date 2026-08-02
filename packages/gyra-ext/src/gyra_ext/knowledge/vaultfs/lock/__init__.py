"""Distributed lock backends for DistributedVaultFS."""

from gyra_ext.knowledge.vaultfs.lock.sql_lock import SQLAdvisoryLock

__all__ = ["SQLAdvisoryLock"]
