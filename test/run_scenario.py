"""Runs the real gazette_watcher pipeline (unmodified) against the local fake
site instead of the live one, using an isolated state dir + log file so
production state is never touched.

Usage: python run_scenario.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gazette_watcher import config, watcher  # noqa: E402

FAKE_URL = "http://localhost:8791/rubrique/fake"

config.RUBRIQUES = [{"key": "faketest", "label": "Fake Test Site", "url": FAKE_URL}]
config.STATE_DIR = PROJECT_ROOT / "test" / "state"
config.LOG_FILE = PROJECT_ROOT / "test" / "watcher_test.log"

if __name__ == "__main__":
    watcher.run()
