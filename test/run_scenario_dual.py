"""Same as run_scenario.py but configures TWO fake rubriques, mirroring the
real two-page production setup — for testing cross-rubrique behavior (e.g.
worst-case notification count/pacing when both pages have a backlog).
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gazette_watcher import config, watcher  # noqa: E402

config.RUBRIQUES = [
    {"key": "faketest-a", "label": "Fake Site A", "url": "http://localhost:8791/rubrique/fake-a"},
    {"key": "faketest-b", "label": "Fake Site B", "url": "http://localhost:8791/rubrique/fake-b"},
]
config.STATE_DIR = PROJECT_ROOT / "test" / "state"
config.LOG_FILE = PROJECT_ROOT / "test" / "watcher_test.log"

if __name__ == "__main__":
    watcher.run()
