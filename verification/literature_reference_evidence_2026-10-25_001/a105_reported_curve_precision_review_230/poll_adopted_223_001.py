"""Poll original223 OS identities; cross-agent tool handles are not shared."""
from pathlib import Path
import json
import time

HERE = Path(__file__).resolve().parent
OWNER = HERE.parent / 'a105_common_assessment_binding_223'
handoff = json.loads((OWNER / 'SESSION_HANDOFF_001.json').read_text())
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
observations = []
for expected in handoff['processes']:
    path = Path('/proc') / str(expected['pid']) / 'stat'
    item = dict(pid=expected['pid'], expected_start_ticks=expected['start_ticks'])
    try:
        raw = path.read_text()
        fields = raw[raw.rindex(')')+2:].split()
        item.update(state=fields[0], current_start_ticks=fields[19],
                    exact_live_identity=boot == 'd53ef063-e9a7-4ae1-99ad-c64c17bdff26'
                    and fields[19] == str(expected['start_ticks']) and fields[0] != 'Z')
    except FileNotFoundError:
        item.update(process_missing=True, exact_live_identity=False)
    observations.append(item)
result_path = OWNER / 'FROZEN_RESULT_003.json'
result = None
transient = None
if result_path.exists():
    try:
        raw = json.loads(result_path.read_text())
        result = {key: raw[key] for key in ('exit_code', 'elapsed_seconds', 'imports_outside_pin', 'changed_pinned_files')}
    except json.JSONDecodeError:
        transient = 'Result file not yet fully written; this is not terminal evidence.'
value = dict(observed_unix=time.time(), boot_id=boot, processes=observations,
    original_session=handoff['session_id'], root_tool_observation='Unknown process id16086; agent tool handles are not accessible from root.',
    authoritative_process_observation='Exact original OS process identity and durable original result are used; no restart or duplicate launch.',
    result=result, transient=transient,
    controlled_pytest_log_tail=(OWNER / 'FROZEN_TEST_RUN_003.log').read_text()[-300:],
    scope='Original controlled223 test runner lifecycle only. No actual private model contents or configured scientific process touched.')
with (HERE / 'ADOPTED223_PUBLIC_STATUS_001.json').open('x') as stream:
    json.dump(value, stream, indent=2); stream.write('\n')
print(json.dumps(value, indent=2))
