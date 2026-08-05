"""Cidade Zero application package."""

# Runtime guards are imported at package startup so every entrypoint receives
# the same API retry protection without duplicating motor code.
from app import runtime_patches as _runtime_patches  # noqa: F401,E402
