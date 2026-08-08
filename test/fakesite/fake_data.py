import json
from pathlib import Path

DATA_DIR = Path(__file__).parent

# A real gazette-drouot thumbnail, reused here so the toast-image test matches
# production conditions (remote https image, not a local file).
SAMPLE_IMAGE = "https://medias.gazette-drouot.com/prod/medias/mediatheque/193524.jpg"


def _data_file(site: str) -> Path:
    suffix = f"_{site}" if site else ""
    return DATA_DIR / f"articles{suffix}.json"


def _current_max_id(site: str):
    path = _data_file(site)
    if not path.exists():
        return 9000
    articles = json.loads(path.read_text(encoding="utf-8"))
    return max((a["id"] for a in articles), default=9000)


def reset_baseline(n=10, base_url="http://localhost:8791", site="", slug="fake"):
    """Writes n baseline (already-known) articles, oldest test state."""
    articles = []
    next_id = 9000
    for i in range(n):
        next_id += 1
        aid = next_id
        articles.append(
            {
                "id": aid,
                "url": f"{base_url}/article/baseline-{aid}/{aid}",
                "date": "1 juil. 2026",
                "title": f"Baseline article {aid}",
                "excerpt": "Pre-existing article, already seen before any test scenario runs.",
                "result": None,
                "image": None,
            }
        )
    _data_file(site).write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    return articles


def prepend_new(n, label, base_url="http://localhost:8791", with_image=False, with_result=False, site=""):
    """Adds n new articles to the front of the list (newest-first), simulating new posts."""
    path = _data_file(site)
    articles = json.loads(path.read_text(encoding="utf-8"))
    next_id = _current_max_id(site)
    new_ones = []
    for i in range(n):
        next_id += 1
        aid = next_id
        item = {
            "id": aid,
            "url": f"{base_url}/article/{label}-{aid}/{aid}",
            "date": "8 août 2026",
            "title": f"[{label}] New test article #{i + 1} (id {aid})",
            "excerpt": f"Synthetic excerpt for scenario '{label}', article {i + 1} of {n}.",
            "result": "12 340 EUR" if with_result else None,
            "image": SAMPLE_IMAGE if with_image else None,
        }
        new_ones.append(item)
    # newest-first: prepend in reverse so item #1 ends up oldest-of-the-new-batch,
    # matching how a real site would show them after successive publishes.
    articles = list(reversed(new_ones)) + articles
    path.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    return new_ones
