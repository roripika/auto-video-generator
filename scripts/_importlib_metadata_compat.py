"""Compat layer to supply importlib.metadata.packages_distributions on older Python.

Some Google client libraries call ``importlib.metadata.packages_distributions``,
which is only available in the stdlib starting with Python 3.10.  When the user
runs our scripts with Python 3.9 (for example, because their setup fell back to
the system interpreter), those imports crash with
``AttributeError: module 'importlib.metadata' has no attribute 'packages_distributions'``.

This module patches the stdlib module to provide the attribute via the
``importlib_metadata`` backport when available.  The patch is intentionally
best-effort – if anything goes wrong we simply leave the stdlib untouched.
"""

from __future__ import annotations


def ensure_importlib_metadata_compat() -> None:
    try:
        import importlib.metadata as stdlib_metadata  # type: ignore
    except Exception:
        return

    if hasattr(stdlib_metadata, "packages_distributions"):
        return

    try:
        import importlib_metadata as backport  # type: ignore
    except Exception:
        return

    func = getattr(backport, "packages_distributions", None)
    if func is None:
        return

    try:
        setattr(stdlib_metadata, "packages_distributions", func)
    except Exception:
        pass


__all__ = ["ensure_importlib_metadata_compat"]
