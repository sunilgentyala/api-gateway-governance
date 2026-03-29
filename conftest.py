"""
Pytest Configuration
=====================
Shared fixtures and configuration for all tests.
"""

import sys
from pathlib import Path

# Make sure the repo root is always on the Python path
# so tests can import framework modules without installation.
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))
