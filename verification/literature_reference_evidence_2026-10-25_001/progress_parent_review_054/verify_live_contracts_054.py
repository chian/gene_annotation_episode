"""Check actual current opt-in declarations against reviewed complete contracts."""
from datetime import datetime, timezone
import json
from pathlib import Path

from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
DESIGN = BASE / 'a105_ratio_episode_integration_077'
HERE = Path(__file__).resolve().parent
baseline = json.loads((DESIGN / 'BASELINE_DEFAULT_CONTRACTS_001.json').read_text())
expected_enabled = json.loads((DESIGN / 'ENABLED_ASSIGNMENT_SCHEMAS_002.json').read_text())
default = LiteratureEpisodes(None, rate_population=True)
enabled = LiteratureEpisodes(None, rate_population=True, ratio_source_population=True)
assert _population_catalog() == baseline['population_catalog']
assert default._rate_fact_sources() == baseline['fact_sources']
for role, schema in baseline['assignment_schemas'].items():
    assert default.assignment_schema(role) == schema
    assert enabled.assignment_schema(role) == expected_enabled[role]
added = set(enabled._rate_fact_sources()) - set(default._rate_fact_sources())
assert added == {'literature_ratio_source_cells'}
assert enabled._rate_fact_sources()['literature_ratio_source_cells']['report_schema'] == json.loads((DESIGN / 'RETURN_SCHEMA_001.json').read_text())
from gene_annotation_episode.literature_ratio_source_storage import ratio_source_population_schema
assert ratio_source_population_schema() == json.loads((DESIGN / 'REQUEST_SCHEMA_001.json').read_text())
result = {'utc': datetime.now(timezone.utc).isoformat(),
    'actual_default_population_operations': len(baseline['population_catalog']),
    'actual_default_return_namespaces': len(baseline['fact_sources']),
    'complete_default_catalog_and_fact_schemas_equal': True,
    'complete_default_and_enabled_seven_assignment_schemas_equal': True,
    'new_namespace_only': sorted(added), 'full_new_request_and_return_schema_match_reviewed_design': True,
    'scope': 'Actual current declarations only, no Workflow, repository, model or scientific execution'}
with (HERE / 'ACTUAL_CONTRACT_ROOT_RECEIPT_054.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
