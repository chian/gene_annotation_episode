"""Re-execute the reviewed225 source example; this is not cold reconstruction."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNER = HERE.parent / 'a105_reported_curve_precision_228'
PIN = HERE / 'pin_001'
sys.dont_write_bytecode = True
sys.path.insert(0, str(PIN))
from gene_annotation_episode.literature_rate_observation_inputs import (
    read_reported_rate_grid, reported_rate_grid_population_schema, reported_rate_grid_extraction_schema)
from gene_annotation_episode.literature_rate_observation_calculations import (
    populate_reported_curve_precision, reported_curve_precision_request_schema,
    reported_curve_precision_selector_schema, reported_curve_precision_sheet_schema)

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest = json.loads((OWNER / 'MANIFEST_002.json').read_text())
assert all(sha(ROOT / row['path']) == row['sha256'] for row in manifest['files'])
schemas = json.loads((OWNER / 'EXACT_IO_SCHEMAS_001.json').read_text())
assert schemas == dict(grid_population=reported_rate_grid_population_schema(),
    grid_extraction=reported_rate_grid_extraction_schema(), precision_request=reported_curve_precision_request_schema(),
    scalar_selector=reported_curve_precision_selector_schema(), precision_sheet=reported_curve_precision_sheet_schema())
example = json.loads((OWNER / 'POPULATED_ORIGINAL_SOURCE_001.json').read_text())
assert example['measurements_synthetic'] is False and example['new_experiment_run'] is False
saved = example['sheet']; args = saved['extraction']['original_arguments']
case = PIN / 'research/experimental_scoring_review_2026-10-23/a105_precision_population_case_225/originals'
workbook = (case / 'S1Data.xlsx').read_bytes()
article = (case / 'article_text.txt').read_bytes()
contexts = {}
def visit(value):
    if isinstance(value, dict):
        if value.get('kind') == 'context_span': contexts[(value['source_ref'], value['artifact_ref'])] = None
        for child in value.values(): visit(child)
    elif isinstance(value, list):
        for child in value: visit(child)
visit(args)
assert all(artifact == 'artifact_' + hashlib.sha256(article).hexdigest() for _, artifact in contexts)
docs = [dict(source_ref=source, artifact_ref=artifact, content=article) for source, artifact in contexts]
extraction = read_reported_rate_grid(workbook, args,
    artifact_ref='artifact_' + hashlib.sha256(workbook).hexdigest(), context_documents=docs)
assert extraction == saved['extraction']
actual = populate_reported_curve_precision(extraction, saved['request'])
assert actual == saved and len(actual['cells']) == 291
assert actual['calculation_metadata']['physical_preparation_count'] is None
assert actual['calculation_metadata']['published_estimate_covariance'] is None
pin_manifest = json.loads((HERE / 'PIN_001.json').read_text())
assert all(sha(PIN / name) == expected for name, expected in pin_manifest['hashes'].items())
result = dict(passed=True, owner_artifacts_verified=len(manifest['files']), scalar_components_reproduced=291,
    workbook_sha256=hashlib.sha256(workbook).hexdigest(), source_context_sha256=hashlib.sha256(article).hexdigest(),
    source_rate_cells=39, concentration_cells=13, selected_native_headers=6,
    exact_extraction_and_sheet_equal=True, pin_unchanged=True,
    scope='Direct pure reader/calculator re-execution of previously converted225source. No new experimental finding, episode, actual model, cold reconstruction or A105 adequacy claim.')
with (HERE / 'ROOT_PRIMARY_EXAMPLE_001.json').open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(result, indent=2))
