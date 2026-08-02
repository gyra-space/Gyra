"""Builtin feature plugins (official catalog + optional routers)."""

from gyra_app.feature_plugins.catalog import (
    FeaturePluginManifest,
    get_manifest,
    list_manifests,
    merge_catalog_with_state,
)

__all__ = [
    "FeaturePluginManifest",
    "get_manifest",
    "list_manifests",
    "merge_catalog_with_state",
]
