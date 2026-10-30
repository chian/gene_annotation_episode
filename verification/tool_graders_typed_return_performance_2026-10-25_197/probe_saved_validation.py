"""Read-only probe locations and unchanged row snapshots; no Store constructor."""
from pathlib import Path
import hashlib, json, sys
ROOT = Path(__file__).resolve().parents[2]
OWN = Path(sys.argv[2]).resolve()
BASE = ROOT / "verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182"
CANDIDATE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(CANDIDATE))
sys.dont_write_bytecode = True
def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
def records(db):
    return {table: [dict(row) for row in db.execute("SELECT * FROM " + table + " ORDER BY rowid")]
            for table in ("runtime_episodes", "runtime_actions", "runtime_forms", "runtime_report_attempts", "runtime_record_receipts", "runtime_observations")}
