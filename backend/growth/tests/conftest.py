"""Make `growth` importable when pytest is run from the repository root.

These are pure unit tests: no database, no running server, no network. They
must stay that way — the whole point of keeping the engine side-effect free
is that its judgment can be tested against synthetic marketplaces in
milliseconds.
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
