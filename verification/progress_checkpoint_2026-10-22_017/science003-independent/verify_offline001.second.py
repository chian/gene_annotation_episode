"""Independent sealed-public-file proof003 review; no database/application imports."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

INPUT = Path('/tmp/configured-api-science-proof003-R-20261022-7ttdezk2')
OUTPUT = Path('/tmp/configured-api-science-proof003-independent-20261022-001-r0RFt20J')
MANIFEST_SHA = '52e9cfe9c24f26578d8b9f80e6aa8c722823589731bda8bf1f1493d89d9e07a4'
FINDINGS = []
WITNESSES = {}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def path_for(name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'outside input member')
    path = INPUT / relative
    for parent in (path, *path.parents):
        require(not stat.S_ISLNK(parent.lstat().st_mode), 'input symlink')
    return path


def raw(name):
    path = path_for(name)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), 'nonregular input')
        with os.fdopen(descriptor, 'rb', closefd=False) as handle:
            data = handle.read()
        after = os.fstat(descriptor)
        keys = ('st_size', 'st_mtime_ns', 'st_mode', 'st_ino', 'st_dev')
        require(all(getattr(before, key) == getattr(after, key) for key in keys), 'input changed while read')
    finally:
        os.close(descriptor)
    row = {'member': name, 'sha256': sha(data), 'bytes': len(data),
           'mode': format(stat.S_IMODE(after.st_mode), '04o'), 'mtime_ns': after.st_mtime_ns,
           'inode': after.st_ino, 'device': after.st_dev}
    if name in WITNESSES:
        require(WITNESSES[name] == row, 'input witness changed')
    WITNESSES[name] = row
    return data


def read(name):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw(name), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def inventory():
    directories, files = {'.'}, set()
    for parent, child_dirs, child_files in os.walk(INPUT, followlinks=False):
        for name in child_dirs:
            path = Path(parent) / name
            require(stat.S_ISDIR(path.lstat().st_mode), 'non-directory or alias')
            require(stat.S_IMODE(path.lstat().st_mode) == 0o555, 'directory mode not readonly0555')
            directories.add(path.relative_to(INPUT).as_posix())
        for name in child_files:
            files.add((Path(parent) / name).relative_to(INPUT).as_posix())
    return directories, files


def resolved(value, aliases):
    if isinstance(value, str) and value.startswith('@'):
        return aliases[value[1:]]
    if isinstance(value, list):
        return [resolved(item, aliases) for item in value]
    if isinstance(value, dict):
        return {key: resolved(item, aliases) for key, item in value.items()}
    return value


def main_checks():
    require(sha(raw('MANIFEST003.json')) == MANIFEST_SHA, 'manifest authority mismatch')
    manifest = read('MANIFEST003.json')
    require(manifest['aliases'] == [] and manifest['manifest_self_excluded'] is True, 'manifest alias/self contract')
    directories, files = inventory()
    require(stat.S_IMODE(INPUT.lstat().st_mode) == 0o555, 'input root mode')
    require(directories == set(manifest['directories']) and files == set(manifest['files']) | {'MANIFEST003.json'}, 'exact tree membership')
    for name, expected in manifest['files'].items():
        raw(name)  # Sealed engineering logs are hashed only; none is parsed or interpreted.
        require(all(WITNESSES[name][key] == expected[key] for key in ('bytes', 'mode', 'sha256')), 'manifest file mismatch: ' + name)
    require(len(manifest['files']) == manifest['regular_file_count_excluding_manifest'] == 34
            and sum(row['bytes'] for row in manifest['files'].values()) == manifest['regular_bytes_excluding_manifest'] == 13806307, 'manifest totals')
    proof = read('SCIENCE_GAIN003.json')
    public = read('PUBLIC_DATABASE_ROWS003.json')
    gain18 = read('GAIN18_PUBLIC_ROWS003.json')
    run, episode = proof['run_id'], proof['episode_id']
    require(run == 'run_23b029a976e343e2bf3957dcc5d0d2ac', 'actual run identity')
    records = {}
    for captured in (public['records'], gain18['records']):
        for ref, row in captured.items():
            record = decoded(row['data'])
            require(record['id'] == row['id'] == ref and record['record_type'] == row['record_type'], 'public record row identity')
            if ref in records:
                require(records[ref] == record, 'duplicate public record disagreement')
            records[ref] = record
            require(proof['records'][ref] == record, 'proof summary differs from saved public row')
    observations = [decoded(row['observation']) for row in public['observations_after_decision34']]
    require(observations == proof['actual_own_action_observations_after34'], 'own observation capture differs')
    require(len({row['unit_ref']['unit_id'] for row in observations}) == len(observations) == 18, 'own observation identities')
    positives = [row for row in observations if row['step']['marginal_credit'] > 0]
    require([row['decision_index'] for row in positives] == [39, 55]
            and positives == proof['actual_positive_gain_after34'], 'exact positive recorded observations after34')
    assessment_refs = {39: 'assessment_40b9f1991d5139c31739e6fd', 55: 'assessment_850a818195e42ac59fce9d37'}
    actions = {int(key): row for key, row in public['selected_actions'].items()}
    actions[55] = gain18['action55']
    for decision, total, unit in [(39, 17.0, 29), (55, 18.0, 42)]:
        row = actions[decision]
        action, outcome = decoded(row['action']), decoded(row['result'])
        require(row['run_id'] == run and row['episode_id'] == episode and row['decision_index'] == decision, 'action ownership identity')
        require(action['kind'] == 'reason' and row['credit'] == total and outcome['status'] == 'completed'
                and assessment_refs[decision] in outcome['record_refs'], 'reason action completed contribution')
        require(len(action['commit']['assessments']) == 1, 'one committed assessment')
        committed = resolved(action['commit']['assessments'][0], outcome['aliases'])
        ref = outcome['aliases'][committed.pop('alias')]
        committed.pop('expected_revision')
        record = records[ref]
        require(ref == assessment_refs[decision] and all(record[key] == value for key, value in committed.items()), 'action commit differs from actual assessment')
        observation = next(item for item in observations if item['decision_index'] == decision)
        require(observation['unit_ref']['episode_id'] == episode and observation['unit_ref']['unit_index'] == unit
                and observation['step']['credit'] == observation['credit']['credit'] == total
                and observation['step']['marginal_credit'] == 1.0 and observation['step']['is_root'] is True
                and observation['label'] == 'reason:' + str(decision), 'one own scientific observation')
        receipts = public['record_receipts'] + gain18['receipts']
        witnesses = [item for item in receipts if item['record_ref'] == ref]
        require(witnesses and all(item['run_id'] == run and item['episode_id'] == episode
                and item['receipt_kind'] == 'own_action' and item['source_index'] == decision for item in witnesses), 'own-action record receipt')
    call_summaries = []
    for call, total in [(35, 16.0), (39, 16.0), (40, 17.0), (41, 17.0), (55, 17.0), (56, 18.0)]:
        saved = read('public-saved-requests/call-' + str(call) + '.json')
        presentation = saved['model_presentation']
        require(presentation['run_id'] == run and presentation['episode_id'] == episode
                and presentation['before_decision_index'] == call, 'saved parent request ownership')
        views = {'raw': saved['context'], 'model': presentation['context']}
        for kind, context in views.items():
            require(context['goal']['parent_goal_id'] in ('', None), 'parent request is not root')
            require(context['current_credit'] == total and context['investigation_progress']['retained_finding_count'] == total
                    and context['annotation_score'] == 0.36004572009144015, 'recorded independent progress/support channels')
            if str(call) in proof['later_parent_saved_views']:
                capture_digest = proof['later_parent_saved_views'][str(call)]['views'][kind]['model_or_raw_context_sha256_canonical']
                require(sha(canonical(context)) == capture_digest, 'declared capture canonical context hash identity')
            visible = {item['id']: item for item in context['working_state']['assessments']}
            for decision in (39, 55):
                ref = assessment_refs[decision]
                expected_visible = call > decision
                require((ref in visible) == expected_visible and (ref in context['visible_record_refs']) == expected_visible, 'finding visibility before/after own action')
                if expected_visible:
                    require(visible[ref] == records[ref], 'received actual assessment contents differ')
            if call in (40, 56):
                decision = 39 if call == 40 else 55
                require(assessment_refs[decision] in context['last_local_outcome']['record_refs'], 'following call lacks own outcome receipt')
            call_summaries.append({'call_index': call, 'view': kind, 'current_credit': total,
                                   'retained_findings': context['investigation_progress']['retained_finding_count'],
                                   'annotation_support': context['annotation_score']})
    require(actions[38]['credit'] == 16.0 and actions[40]['credit'] == 17.0, 'measurement acquisition / annotation integration recorded totals')
    action40 = decoded(actions[40]['action'])
    require(assessment_refs[39] in canonical(action40).decode(), 'later parent annotation action does not reference finding39')
    counts = public['counts_for_actual_new_run_only']
    require(counts == proof['counts_at_snapshot'] and counts['runtime_commission_intents'] == 0
            and counts['runtime_episodes'] == 1 and gain18['provenance']['commission_count_for_actual_run'] == 0, 'captured no child commissions')
    first = records[assessment_refs[39]]
    require(first['relation'] == 'does_not_discriminate' and first['applicability'] == 'contextual'
            and first['investigation_finding']['status'] == 'retained'
            and first['investigation_finding']['qualification']['kind'] == 'measurement_does_not_establish_claim', 'first limitation meaning')
    comparison = records[first['observation_ref']]
    require(comparison['kind'] == 'comparison' and comparison['source_ref'] == 'source_827720648609fb105f7af587', 'first limitation comparison provenance')
    measurement = {item['name']: item['value'] for item in comparison['measurements']}
    provider = read('public-artifacts/a2194447b305d39b9c959eaa52c678c78103e9cd40f260669f3a4ea994e8ff36.json')
    hit = next(item for item in provider['result']['hits'] if item['metadata']['uniprot_accession'] == 'Q9RXF9')
    domain = next(item for item in hit['domains'] if item['bitscore'] == measurement['bitscore']['value'])
    require(domain['ievalue'] == measurement['evalue']['value']
            and domain['alignment_display']['identity'][0] == measurement['identity_fraction']['value']
            and hit['metadata']['description'] == records[measurement['reference_ref']['ref']]['label'] == 'Exodeoxyribonuclease III', 'copied public measurement values/label')
    second = records[assessment_refs[55]]
    finding = second['investigation_finding']
    observation = records[second['observation_ref']]
    source_subject = records[finding['source_claim']['subject_refs'][0]]
    hypothesis = records[second['hypothesis_ref']]
    require(second['relation'] == 'does_not_discriminate' and second['applicability'] == 'incomparable'
            and finding['status'] == 'retained' and finding['qualification']['kind'] == 'different_source_subject', 'second transfer limitation meaning')
    require(source_subject['label'] == 'DrXth' and source_subject['id'] != hypothesis['subject_refs'][0]
            and hypothesis['subject_refs'] == ['input_a5c60b96717424cdf5138420']
            and observation['subject_refs'] == observation['source_subject_refs'] == [source_subject['id']], 'DrXth source subject distinct from fixed target')
    anchors = []
    for ref, record in records.items():
        anchor = record.get('anchor')
        if anchor is None:
            continue
        artifact = anchor['artifact_ref']
        name = next(name for name in manifest['files'] if name.startswith('public-artifacts/' + artifact[9:] + '.'))
        data = raw(name)
        selected = data[anchor['start']:anchor['end']]
        require(selected == anchor['quote'].encode('utf-8'), 'source byte anchor mismatch: ' + ref)
        require(anchor['source_ref'] == record['source_ref'], 'anchor/record source mismatch')
        anchors.append({'record_ref': ref, 'source_ref': record['source_ref'], 'artifact_ref': artifact,
                        'start_utf8_byte': anchor['start'], 'end_utf8_byte': anchor['end'], 'selected_sha256': sha(selected)})
    require(len(anchors) == 5 and {item['selected_sha256'] for item in anchors} == {'4b054af545ff06b53c0d5828b22949bf0112ae1d374b64886fb5a54803f5f8ac'}, 'five shared public source anchors')
    context_quote = records[finding['qualification']['context_refs'][0]]['anchor']['quote']
    require('Deinococcus radiodurans (DrXth)' in context_quote and 'THF.T' in context_quote
            and 'YbhP' not in context_quote and 'b0790' not in context_quote, 'source-subject applicability text')
    for name in list(WITNESSES):
        raw(name)
    require(inventory() == (directories, files), 'input membership changed after review')
    FINDINGS.extend([
        {'claim': 'exact_sealed_membership', 'regular_members_including_manifest': 35, 'directories': 3, 'aliases': 0,
         'declared_bytes_excluding_manifest': 13806307, 'manifest_sha256': MANIFEST_SHA},
        {'claim': 'two_recorded_own_reason_gains', 'decisions': [39, 55], 'observation_units': [29, 42],
         'recorded_progress': [16, 17, 18], 'recorded_marginal_credit_each': 1.0, 'score_recomputed': False},
        {'claim': 'later_parent_receives_records', 'following_calls': [40, 56], 'raw_and_presented_views_checked': True,
         'annotation_action40_references_assessment39': True, 'call_summaries': call_summaries},
        {'claim': 'annotation_support_separate_and_unchanged', 'recorded_value': 0.36004572009144015},
        {'claim': 'captured_no_child_commissions', 'commission_intents': 0, 'episodes': 1,
         'meaning': 'captured snapshot counts, not independent exhaustive live history'},
        {'claim': 'source_anchor_applicability', 'anchors': anchors, 'source_subject': 'DrXth / Deinococcus radiodurans',
         'fixed_target_ref': hypothesis['subject_refs'][0], 'qualification': 'different_source_subject',
         'entailment_limit': 'no target AP-endonuclease activity, absence, localization or enzyme assignment established'},
    ])
    return {'version': 'independent_public_science_proof003_review_v1', 'status': 'verified_with_limits',
            'input_root': str(INPUT), 'run_id': run, 'episode_id': episode, 'findings': FINDINGS,
            'input_witnesses': [WITNESSES[name] for name in sorted(WITNESSES)],
            'limits': ['sealed captured public files only; no new capture or live/database access',
                       'recorded credit/progress/support compared without score or projector recomputation',
                       'raw/presented saved requests establish supplied information, not private model reasoning or causation',
                       'action40 explicitly uses assessment39; call56 establishes receipt of assessment55, not a later completed integration action',
                       'zero commission counts apply to captured snapshots; no child contribution demonstrated',
                       'byte anchors establish copied text consistency, not independent assay validity or applicability to YbhP',
                       'no forecast-informed choice, scientific completion or whole-goal completion proved',
                       'initial followup observer failure remains retained in input bundle; no failure file deleted']}


def save(name, value):
    path = OUTPUT / name
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(canonical(value) + b'\n')
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == '__main__':
    try:
        result = main_checks()
        code = 0
    except Exception as error:
        result = {'version': 'independent_public_science_proof003_review_v1', 'status': 'failed',
                  'error_type': type(error).__name__, 'error': str(error), 'completed_findings': FINDINGS,
                  'input_witnesses': [WITNESSES[name] for name in sorted(WITNESSES)]}
        code = 1
    save('RESULT002.json', result)
    print(json.dumps({'status': result['status'], 'result': str(OUTPUT / 'RESULT002.json')}))
    raise SystemExit(code)
