"""Planning-only JSON Schema checks; never imports the application or opens SQLite."""
from copy import deepcopy
from pathlib import Path
import json
from jsonschema import Draft202012Validator

bundle = Path('/tmp/scientific-checkpoint-custody-contract-20261022-002-hb8UUg')
schema = json.loads((bundle / 'SCHEMAS004.json').read_text())
Draft202012Validator.check_schema(schema)
objects = []
def walk(value):
    if isinstance(value, dict):
        if value.get('type') == 'object':
            objects.append(value)
            assert value.get('additionalProperties') is False
        for child in value.values(): walk(child)
    elif isinstance(value, list):
        for child in value: walk(child)
walk(schema)
validator = Draft202012Validator(schema['$defs']['failure'])
base = dict(version='scientific_checkpoint_fork_failure_v1', code='publication_failure',
    phase='publish', affected_refs=['/tmp/private-requested-destination'],
    staging_workspace=None, published_workspace=None, publication_state='not_created',
    source_unchanged=True, cause='contract_error', errno=None)
positive = []
for state, stage, published, cause in [
    ('not_created', None, None, 'contract_error'),
    ('retained_stage', '/tmp/private-stage', None, 'contract_error'),
    ('retained_stage', None, None, 'io_error'),
    ('published_durability_unconfirmed', None, '/tmp/private-published', 'io_error'),
    ('published_durability_unconfirmed', None, None, 'io_error'),
    ('published_location_unconfirmed', None, '/tmp/private-moved/published', 'contract_error'),
    ('published_location_unconfirmed', None, None, 'io_error')]:
    item = dict(base, publication_state=state, staging_workspace=stage,
                published_workspace=published, cause=cause)
    validator.validate(item)
    positive.append(item)
negative = []
def reject(original, **changes):
    item = dict(deepcopy(original), **changes)
    assert not validator.is_valid(item), item
    negative.append(item)
reject(positive[0], staging_workspace='/tmp/stale-stage')
reject(positive[0], published_workspace='/tmp/stale-published')
reject(positive[1], published_workspace='/tmp/forbidden-published')
reject(positive[1], staging_workspace='relative-stage')
reject(positive[3], staging_workspace='/tmp/old-stage-name')
reject(positive[3], cause='contract_error')
reject(positive[5], source_unchanged=False)
reject(positive[5], phase='snapshot')
reject(positive[5], code='storage_failure')
reject(positive[5], published_workspace='relative-published')
reject(positive[0], invented_extra_key=True)
print(json.dumps(dict(status='representation_only_passed', definitions=len(schema['$defs']),
    closed_object_schemas=len(objects), positive_failure_examples=len(positive),
    negative_failure_examples=len(negative), application_imports=0, database_opens=0,
    filesystem_race_fixtures_run=0), sort_keys=True))
