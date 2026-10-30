"""Retain complete original-report measurements, never abbreviated previews."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from test_rfam_batch_report import actual_case, one_query, synthetic, parse, calculate, project
from gene_annotation_episode.rfam_batch_report_contracts import REPORT_METRIC_DEFINITIONS

out = Path(sys.argv[1])
def write(name, value):
 (out / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')

original = actual_case()
result = parse(original)
sheet = result['sheet']
calculation = calculate(sheet)
for name, value in (('native.parse.json', result), ('native.sheet.json', sheet),
 ('native.calculation.json', calculation), ('native.hit-projection.json', project(sheet, calculation)),
 ('native.strand-projection.json', project(sheet, calculation, family='query_strand')),
 ('metric-definitions.json', REPORT_METRIC_DEFINITIONS)):
 write(name, value)

case = one_query()
text = case[0].decode()
score = next(line for line in text.splitlines() if line.lstrip().startswith('(1)'))
display = text[text.index('>>'):text.index('Internal CM pipeline')]
duplicate = text.replace(score, score + '\n' + score.replace('(1)', '(2)'), 1)
duplicate = duplicate.replace(display, display + display.replace('(1)', '(2)'), 1)
duplicate = re.sub(r'Total CM hits reported:\s+1', 'Total CM hits reported: 2', duplicate)
zero = text[:text.index('Hit scores:')] + 'Hit scores:\n\n   [No hits detected that satisfy reporting thresholds]\n\nHit alignments:\n\n   [No hits detected that satisfy reporting thresholds]\n\n' + text[text.index('Internal CM pipeline'):]
zero = re.sub(r'Total CM hits reported:\s+1', 'Total CM hits reported: 0', zero)
for label, modified in (('synthetic-duplicate', duplicate), ('synthetic-zero', zero)):
 fixture = synthetic(case, modified.encode())
 parsed = parse(fixture)
 write(label + '.parse.json', parsed)
 write(label + '.calculation.json', calculate(parsed['sheet']))
 (out / (label + '.out')).write_bytes(fixture[0])

sources = [ROOT / sheet['capture']['artifact_ref'], ROOT / sheet['capture']['source_ref'],
 ROOT / sheet['input_identity']['submission_source_ref'],
 ROOT / 'verification/tool_graders_rfam_transport_2026-10-26_234/live/multi/input.seq',
 ROOT / 'verification/tool_graders_rfam_transport_2026-10-26_234/live/multi/input-manifest.json',
 ROOT / 'resources/software/infernal-1.1.5/src/cm_alidisplay.c',
 ROOT / 'resources/software/infernal-1.1.5/src/cm_tophits.c']
write('provenance.json', [{'path': str(p), 'bytes': p.stat().st_size,
 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources])
summary = [{'query': hit['native_query_name'], 'strand': hit['strand'],
 'score_bits': hit['native_score_bits'], 'span': hit['query_span_nt'],
 'native_model_span': hit['native_model_span_positions'],
 'represented_model': hit['represented_model_positions'], 'represented_query': hit['represented_query_positions'],
 'compared': hit['model_consensus_compared_count'], 'equal': hit['model_consensus_equal_count'],
 'inserted': hit['query_insert_count'], 'deleted': hit['model_delete_count'],
 'truncated_3p': hit['truncated_model_count_3p'], 'model_length': hit['model_length_positions']}
 for hit in calculation['hits']]
write('summary.json', summary)
print(json.dumps({'parse_status': result['status'], 'population_complete': sheet['population_complete'],
 'rows': summary}, indent=2))
