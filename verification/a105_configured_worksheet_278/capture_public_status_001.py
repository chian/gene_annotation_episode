"""One operator snapshot, without adding a runtime/controller observation."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
status = json.loads(subprocess.check_output([sys.executable, '-B', str(here/'public_status_002.py')], text=True))
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
target = here/('PUBLIC_STATUS_'+stamp+'.json')
target.write_text(json.dumps(status, indent=2)+'\n')
print(json.dumps({'receipt': str(target), 'observed_at_utc': status['observed_at_utc'],
    'confirmed_original_process_live': status['confirmed_original_process_live'],
    'state': status['run'][0]['state'], 'counts': status['counts'],
    'model_call_completion_counts': status['model_call_completion_counts'],
    'selected_action_categories': status['selected_action_categories'],
    'deliveries': status['deliveries']}, indent=2))
