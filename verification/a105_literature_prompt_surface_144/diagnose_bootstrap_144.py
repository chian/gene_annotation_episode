"""Synthetic default-science bootstrap; stop before provider entry or transport."""
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from gene_annotation_episode.providers import ModelConnection

class PretransportSentinel(RuntimeError):
    pass

async def stop_before_transport(self):
    raise PretransportSentinel('controlled_pretransport_stop')

def diagnose(folder):
    folder.mkdir(exist_ok=False)
    source=folder/'synthetic_source.html'
    raw=b'<html><body>Synthetic engineering bootstrap; no biological measurements.</body></html>'
    source.write_bytes(raw)
    spec=importlib.util.spec_from_file_location('bootstrap_caller_144',HERE/'run_configured_primary_144.py')
    caller=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(caller)
    prepared=caller.prepare(folder/'prepared',source=source,source_sha256=hashlib.sha256(raw).hexdigest(),
        question='Evaluate the selected synthetic source experiment within its reference-only scope.')
    original=ModelConnection.__aenter__
    ModelConnection.__aenter__=stop_before_transport
    try:
        asyncio.run(caller.execute(folder/'prepared',prepared))
    except Exception as error:
        record={'exception_type':type(error).__name__,'message':str(error),
            'failure':getattr(error,'failure',None),'pretransport_sentinel_reached':isinstance(error,PretransportSentinel),
            'actual_model_started':False,'source':'synthetic engineering fixture'}
        (folder/'traceback.txt').write_text(traceback.format_exc())
        with sqlite3.connect(folder/'prepared/state/state.sqlite3') as db:
            tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            record['runtime_counts']={table:(db.execute('SELECT count(*) FROM '+table).fetchone()[0] if table in tables else None)
                for table in ('runtime_runs','runtime_episodes','runtime_actions','runtime_observations','runtime_report_attempts')}
        (folder/'diagnostic.json').write_text(json.dumps(record,indent=2)+'\n')
        return record
    finally:
        ModelConnection.__aenter__=original

if __name__=='__main__':
    folder=Path(sys.argv[1]).resolve()
    print(json.dumps(diagnose(folder),indent=2))
