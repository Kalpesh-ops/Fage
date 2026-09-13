"""Print the reconstructed forecast for one or more sample users (dev tool)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code"))

from fage import forecast  # noqa: E402
from fage.loader import load, load_sample_labels  # noqa: E402

ds = load(ROOT / "dataset")
labels = load_sample_labels(ROOT / "dataset")
reqs = {r.user_id: r for r in ds.sample_requests + ds.requests}
for a in sys.argv[1:]:
    uid = f"user_{int(a):02d}"
    req = reqs[uid]
    prof = ds.profiles[uid]
    fc = forecast.build(prof, ds.events_by_user[uid], req.date, ds.fx)
    print("=" * 20, uid, req.request_id, req.date, "bal", prof.balance, "min", prof.minimum, "req", req.amount, labels.get(req.request_id))
    for n in fc.notes:
        print("  NOTE", n)
    series = fc.daily()
    bal = dict(series)
    for f in sorted(fc.flows, key=lambda f: (f.date, f.amount)):
        if f.date <= fc.end:
            print(f"  {f.date} {f.amount:>14} {f.kind:18} {f.source:40} bal={bal.get(max(f.date, fc.start))}")
    low = min(series, key=lambda x: x[1])
    print("  LOW", low, "safe", low[1] - prof.minimum)
