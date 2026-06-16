from __future__ import annotations

import os
import sys

import pytest

# Ensure src is importable without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set a fake NEWS_API_KEY so Settings() doesn't fail during app creation
os.environ.setdefault("NEWS_API_KEY", "test-key-for-tests")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "development")
