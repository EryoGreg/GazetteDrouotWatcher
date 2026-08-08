"""Points at the fake Cloudflare-challenge-mimicking endpoint, to test the
block-detection + alert-with-cooldown path without needing a real block."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gazette_watcher import config, watcher  # noqa: E402

config.RUBRIQUES = [
    {"key": "faketest-blocked", "label": "Fake Blocked Site", "url": "http://localhost:8791/rubrique/blocked"},
]
config.STATE_DIR = PROJECT_ROOT / "test" / "state"
config.LOG_FILE = PROJECT_ROOT / "test" / "watcher_test.log"

if __name__ == "__main__":
    watcher.run()
