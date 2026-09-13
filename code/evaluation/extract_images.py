"""Run (or replay from cache) the image extraction layer for all images and print the result."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from fage.evidence import extract_image  # noqa: E402
from fage.loader import load  # noqa: E402
from fage.providers import ModelClient  # noqa: E402

ds = load(ROOT / "dataset")
client = ModelClient(ROOT / "code" / "cache", ROOT / "code" / "evaluation" / "call_ledger.jsonl", offline="--offline" in sys.argv)
for uid, imgs in ds.images_by_user.items():
    evs = {e.event_id: e for e in ds.events_by_user[uid]}
    for img in imgs:
        am, rej = extract_image(client, img, evs[img.related_event_id])
        print(img.image_id, img.related_event_id, evs[img.related_event_id].description, "->", am.value if am else None, am.note if am else rej)
