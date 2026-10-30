"""Capture one actual public scientific contribution; no runtime mutation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import sqlite3

RUN = Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-006')
OUT = Path('/tmp/configured-caller-actual-science-20261022-001')
OUT.mkdir(mode=0o700)
run_id = json.loads((RUN / 'run.json').read_text())['run_id']
committed = {row['reference'] for row in json.loads(
    (RUN / 'workspace/checkpoint/committed-references.json').read_text())['records']}


def save(name, value):
    with (OUT / name).open('x') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def witness(path):
    body = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}


def contains_record(value, reference):
    if isinstance(value, dict):
        return value.get('id') == reference or any(contains_record(v, reference) for v in value.values())
    if isinstance(value, list):
        return any(contains_record(v, reference) for v in value)
    return False


db = sqlite3.connect((RUN / 'workspace/state.sqlite3').as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
try:
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    def get(reference):
        row = db.execute('SELECT data FROM records WHERE id=?', (reference,)).fetchone()
        assert row is not None
        return json.loads(row['data'])
    selected = db.execute('SELECT * FROM runtime_actions WHERE run_id=? AND decision_index=13',
                          (run_id,)).fetchone()
    action, result = json.loads(selected['action']), json.loads(selected['result'])
    assert action['kind'] == 'reason' and result['status'] == 'completed' and selected['credit'] == 13.0
    assessment_ref = result['aliases']['prior_location_conflict']
    assessment = get(assessment_ref)
    assert assessment_ref not in committed
    assert assessment['relation'] == 'weakens' and assessment['applicability'] == 'transfer'
    finding = assessment['investigation_finding']
    assert finding['qualification']['kind'] == 'alternatives_not_discriminated'
    observation = get(assessment['observation_ref'])
    assert observation['kind'] == 'source_annotation'
    hypothesis = get(assessment['hypothesis_ref'])
    question_term = get(hypothesis['value']['ref'])
    claim_term = get(finding['source_claim']['value']['ref'])
    assert question_term['label'] == 'IM' and claim_term['label'] == 'Cytoplasm'
    protein = get(finding['source_claim']['subject_refs'][0])
    assert protein['accession'] == 'P0AAW1' and protein['length'] == 253
    original_source = get(observation['source_ref'])
    workbook = get(original_source['parent_source_refs'][0])
    header_source = get('source_a0387d8288acd8b364819ead')
    assert original_source['id'] in committed and workbook['id'] in committed
    assert header_source['id'] not in committed
    artifacts = {}
    def artifact(reference):
        checksum = reference.removeprefix('artifact_')
        path = RUN / 'workspace/artifacts' / checksum[:2] / checksum
        body = path.read_bytes()
        assert hashlib.sha256(body).hexdigest() == checksum
        artifacts[reference] = witness(path)
        with (OUT / (reference + '.json')).open('xb') as stream:
            stream.write(body)
        return body
    row_bytes = artifact(original_source['artifact_ref'])
    rows = json.loads(row_bytes)
    header = json.loads(artifact(header_source['artifact_ref']))
    anchor = observation['anchor']
    assert row_bytes[anchor['start']:anchor['end']].decode() == anchor['quote']
    columns = {cell['address']: cell['value'] for cell in header['header']['cells']}
    cells = {cell['address']: cell['value'] for cell in rows['rows'][0]['cells']}
    assert columns['R1'] == 'STEPdb_loc_code'
    assert columns['Y1'] == 'localization (sucrose gradient)'
    assert cells['B1324'] == 'P0AAW1' and cells['R1324'] == 'Cytoplasm' and cells['Y1324'] == 'IM'
    observations = []
    for row in db.execute('SELECT unit_index,observation FROM runtime_observations WHERE run_id=?', (run_id,)):
        value = json.loads(row['observation'])
        if value.get('decision_index') == 13:
            observations.append(value)
    assert len(observations) == 1
    own = observations[0]
    assert own['unit_ref']['unit_index'] == 8
    assert own['step']['marginal_credit'] == 1.0 and own['step']['estimate']['turns'] == 9
    assert own['step']['stop'] is False
    next_raw = db.execute('SELECT request FROM runtime_model_calls WHERE run_id=? AND call_index=14',
                         (run_id,)).fetchone()['request']
    request = json.loads(next_raw)
    context, model = request['context'], request['model_presentation']['context']
    for value in (context, model):
        assert value['current_credit'] == 13.0
        assert value['investigation_progress']['retained_finding_count'] == 13
        assert all(v == 0.0 for v in value['annotation_evidence_vector'].values())
        assert contains_record(value['working_state'], assessment_ref)
    old_locations = []
    for row in db.execute("SELECT id,data FROM records WHERE record_type='assessment'"):
        if row['id'] not in committed:
            continue
        old = json.loads(row['data'])
        if get(old['hypothesis_ref'])['predicate'] == 'located_in':
            old_locations.append(old)
    assert len(old_locations) == 1
    assert old_locations[0]['investigation_finding']['source_claim']['value']['ref'] == question_term['id']
    assert old_locations[0]['investigation_finding']['qualification']['kind'] == 'measurement_does_not_establish_claim'
    receipt = db.execute('SELECT receipt_kind,source_index FROM runtime_record_receipts '
                        'WHERE run_id=? AND episode_id=? AND record_ref=?',
                        (run_id, selected['episode_id'], assessment_ref)).fetchone()
    assert receipt['receipt_kind'] == 'own_action' and receipt['source_index'] == 13
    counts = {table: db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=?',
               (run_id,)).fetchone()[0] for table in
               ('runtime_actions', 'runtime_observations', 'runtime_commission_intents', 'runtime_episodes')}
    payload = {'captured_at': datetime.now(timezone.utc).isoformat(), 'run_id': run_id,
        'episode_id': selected['episode_id'], 'decision_index': 13,
        'action': action, 'result': result, 'assessment': assessment,
        'observation': observation, 'hypothesis': hypothesis, 'question_term': question_term,
        'claim_term': claim_term, 'protein': protein, 'original_source': original_source,
        'workbook_source': workbook, 'header_source': header_source,
        'old_inherited_location_assessments': old_locations,
        'original_completed_own_observation': own, 'actual_receipt': dict(receipt),
        'next_decision': {'call_index': 14,
            'request_raw_utf8_sha256': hashlib.sha256(next_raw.encode()).hexdigest(),
            'request_raw_utf8_bytes': len(next_raw.encode()),
            'raw_and_model_visible_assessment': True, 'scientific_progress': 13.0,
            'annotation_evidence_vector': context['annotation_evidence_vector'],
            'annotation_score': context['annotation_score']},
        'source_cells': {'gene': cells['A1324'], 'protein': cells['B1324'],
            columns['R1']: cells['R1324'], columns['Y1']: cells['Y1324']},
        'artifact_witnesses': artifacts, 'snapshot_counts': counts,
        'meaning': 'A new typed qualification records the STEPdb Cytoplasm assertion as opposing the IM localization hypothesis while leaving alternatives undiscriminated. It does not establish a location or molecular function.',
        'not_claimed': ['new independent experiment', 'resolved target function or localization',
                        'scientific child return or parent use of child information',
                        'whole-goal completion'],
        'access': 'One readonly/query_only NEW active workspace connection; original DB/Store/private provider events were not opened.'}
finally:
    db.close()
save('SCIENCE_GAIN001.json', payload)
save('READSET001.json', {'files': [witness(Path(__file__))] +
    [witness(CODE / 'gene_annotation_episode' / name) for name in
     ('investigation_progress.py', 'scientific_findings.py', 'finding_validity.py')] +
    [witness(RUN / 'workspace/checkpoint/committed-references.json')],
    'application_imports_or_constructors': 0, 'database_write_connections': 0,
    'model_http_native_or_test_calls': 0})
members = {p.name: witness(p) for p in sorted(OUT.iterdir()) if p.is_file()}
save('MANIFEST001.json', {'version': 'actual_scientific_gain_evidence_v1', 'members': members})
for path in OUT.iterdir():
    path.chmod(0o444)
OUT.chmod(0o555)
print(json.dumps({'evidence': str(OUT), 'scientific_progress': '12 to 13',
                  'annotation_support_vector': payload['next_decision']['annotation_evidence_vector'],
                  'actual_own_action_observations_for_contribution': 1,
                  'child_influence_demonstrated': False, 'snapshot_counts': counts}, sort_keys=True))
