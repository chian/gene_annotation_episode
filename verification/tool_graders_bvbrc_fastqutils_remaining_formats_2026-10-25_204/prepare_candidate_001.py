"""Create an isolated extension of the verified 198 return-revision snapshot."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from pprint import pformat
import shutil

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/return_revision_002'
DEST = HERE / 'candidate'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


before = json.loads((PREVIOUS / 'source_after.json').read_text())
assert {name: sha(PREVIOUS / 'candidate' / name) for name in before} == before
DEST.mkdir(exist_ok=False)
for name in before:
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PREVIOUS / 'candidate' / name, target)
save('BASELINE_MANIFEST_001.json', before)

sections = ['cutadapt_summary', 'cutadapt_adapter', 'cutadapt_adapter_errors',
            'cutadapt_adapter_histogram', 'cutadapt_adjacent_bases', 'cutadapt_poly_a']
populations = ['cutadapt_' + key for key in (
    'input_reads', 'input_pairs', 'output_reads', 'output_pairs', 'input_bases',
    'output_bases', 'mate_input_bases', 'mate_output_bases', 'adapter_reads',
    'filtered', 'reverse_complemented', 'quality_removed', 'poly_a_removed',
    'adapter_events', 'poly_a_events')]

# Native extraction definitions only. No score evaluator or formula DSL.
# name, section, native field, units, axes, populations, interpretation
rows = [
 ('processed_count', 'summary', 'Total reads/read pairs processed', ['reads','pairs'], ['none'], ['input_reads','input_pairs'], 'Exact processed input count according to native single or paired mode.'),
 ('adapter_containing_reads', 'summary', 'Reads with adapters / Read 1 or 2 with adapter', ['reads'], ['none','native_label'], ['adapter_reads'], 'Reads with at least one adapter, separately for each explicitly reported mate.'),
 ('reverse_complemented_count', 'summary', 'Reverse-complemented', ['reads','pairs'], ['none'], ['reverse_complemented'], 'Native selected-orientation count, distinct from adapter event multiplicity.'),
 ('filtered_count', 'summary', 'Read fate breakdown: native filter label', ['reads','pairs'], ['native_label'], ['filtered'], 'Native count for the exact named filter; omitted filters remain absent.'),
 ('written_count', 'summary', 'Reads/Pairs written (passing filters)', ['reads','pairs'], ['none'], ['output_reads','output_pairs'], 'This Cutadapt invocation output before any later Trim Galore filters.'),
 ('processed_bases', 'summary', 'Total basepairs processed / Read 1 / Read 2', ['bases'], ['none','native_label'], ['input_bases','mate_input_bases'], 'Total input bases and explicitly printed per-mate input bases.'),
 ('quality_trimmed_bases', 'summary', 'Quality-trimmed / Read 1 / Read 2', ['bases'], ['none','native_label'], ['quality_removed'], 'Reported bases removed by quality trimming, preserving total versus mate.'),
 ('poly_a_trimmed_bases', 'summary', 'Poly-A-trimmed / Read 1 / Read 2', ['bases'], ['none','native_label'], ['poly_a_removed'], 'Reported bases removed by poly-A trimming, preserving total versus mate.'),
 ('written_bases', 'summary', 'Total written (filtered) / Read 1 / Read 2', ['bases'], ['none','native_label'], ['output_bases','mate_output_bases'], 'Output bases for the exact invocation and explicitly reported mate.'),
 ('reported_percent', 'summary', 'Parenthesized percentage accompanying a native summary count', ['percent'], ['native_label'], ['input_reads','input_pairs','input_bases','adapter_reads','filtered','reverse_complemented','output_reads','output_pairs','quality_removed','poly_a_removed','output_bases'], 'One-decimal native proportion. The exact count and native row locator remain separate.'),
 ('adapter_length', 'adapter', 'Length', ['bases'], ['none','native_label'], ['adapter_events'], 'Native adapter parameter; linked front and back lengths remain separate.'),
 ('adapter_trimmed_count', 'adapter', "Trimmed / 5\u0027 trimmed / 3\u0027 trimmed", ['native_count'], ['none','native_label'], ['adapter_events'], 'Adapter match/removal events; a read can contribute multiple events.'),
 ('adapter_reverse_complemented_count', 'adapter', 'Reverse-complemented', ['native_count'], ['none'], ['adapter_events'], 'Native adapter-associated reverse-complemented counter.'),
 ('minimum_overlap', 'adapter_errors', 'Minimum overlap', ['bases'], ['none','native_label'], ['adapter_events'], 'Native minimum-overlap parameter, separated by linked adapter end.'),
 ('allowed_errors', 'adapter_errors', 'No. of allowed errors', ['native_count'], ['none','length_closed'], ['adapter_events'], 'Configured errors for the native closed length interval; no inferred interval for an anchored scalar.'),
 ('histogram_length', 'adapter_histogram', 'length', ['bases'], ['length_closed'], ['adapter_events'], 'Removed length, potentially including flanking bases; not aligned adapter length.'),
 ('histogram_count', 'adapter_histogram', 'count', ['native_count'], ['length_closed'], ['adapter_events'], 'Adapter removal events at the exact removed length and native end.'),
 ('histogram_expected_count', 'adapter_histogram', 'expect', ['native_count'], ['length_closed'], ['adapter_events'], 'Native chance-model expectation rounded to one decimal; retain the reported model value.'),
 ('histogram_max_errors', 'adapter_histogram', 'max.err', ['native_count'], ['length_closed'], ['adapter_events'], 'Nominal native configured error bound, distinct from observed error bins.'),
 ('histogram_error_count', 'adapter_histogram', 'error counts', ['native_count'], ['edit_error_count'], ['adapter_events'], 'Count for each explicit error-index bin. Same section/row ordinal joins it to removed length.'),
 ('adjacent_base_percent', 'adjacent_bases', 'Bases preceding removed adapters: A/C/G/T/none-other', ['percent'], ['symbol'], ['adapter_events'], 'Native rounded adjacent-base percentage; text does not provide base counts.'),
 ('poly_a_length', 'poly_a', 'length', ['bases'], ['length_closed'], ['poly_a_events'], 'Removed poly-A length for the native mate-specific histogram.'),
 ('poly_a_count', 'poly_a', 'count', ['reads'], ['length_closed'], ['poly_a_events'], 'Reads at the native removed poly-A length; preserve mate identity.'),
]
specs = {}
configuration = {'adapter_length', 'minimum_overlap', 'allowed_errors', 'histogram_max_errors'}
percentages = {'reported_percent', 'adjacent_base_percent'}
for name, section, native_field, units, axes, keys, meaning in rows:
    metric = 'cutadapt_' + name
    estimate = name == 'histogram_expected_count'
    percentage = name in percentages
    config = name in configuration
    specs[metric] = {
        'metric': metric, 'formats': ['trim_galore_report_0_6_10'],
        'section_key': 'cutadapt_' + section, 'native_fields': [native_field],
        'units': units, 'axis_kinds': axes, 'population_keys': ['cutadapt_' + k for k in keys],
        'meaning': 'native_estimate' if estimate else 'native_normalized' if percentage else 'native_configuration' if config else 'observed_count',
        'precision': 'native_rounded' if percentage else 'native_estimator' if estimate else 'exact_for_retained_population',
        'value_domain': 'nonnegative_number' if percentage or estimate else 'nonnegative_integer',
        'interpretation': meaning,
        'denominator': ('Native named row input reads/pairs or total input bases, as recorded separately in the same invocation.' if name == 'reported_percent' else 'Native adjacent-base observation population, whose exact count is not printed.' if name == 'adjacent_base_percent' else 'Native processed count and nucleotide chance model; preserve printed expectation without substituting assumptions.' if estimate else None),
        'coordinates': ('Native closed length interval; histogram rows join by section and row ordinal.' if 'length_closed' in axes else 'Observed edit-error index; removed length comes from the same native section/row.' if 'edit_error_count' in axes else 'not_applicable'),
        'uncertainty': 'native_reporting_precision' if percentage or estimate else 'not_reported',
        'missing_behavior': 'Retain the native token and explicit missing/malformed/partial state. Omitted is not zero; preserve independent valid siblings. Do not reconstruct missing counts from percentages.',
        'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d',
    }

module = DEST / 'gene_annotation_episode/bvbrc_fastqutils_cutadapt_specs.py'
module.write_text('"""Native Cutadapt field meanings; calculations remain separate functions."""\n\nCUTADAPT_METRICS = ' + pformat(specs, width=110, sort_dicts=False) + '\n')
metric_module = DEST / 'gene_annotation_episode/bvbrc_fastqutils_metric_specs.py'
text = metric_module.read_text()
assert text.count('METRIC_ORDER = tuple(_METRICS)') == 1
text = text.replace('METRIC_ORDER = tuple(_METRICS)',
    'from .bvbrc_fastqutils_cutadapt_specs import CUTADAPT_METRICS\n\n'
    '_METRICS.update(CUTADAPT_METRICS)\n\nMETRIC_ORDER = tuple(_METRICS)')
metric_module.write_text(text)

schema_file = DEST / 'gene_annotation_episode/bvbrc_fastqutils_schemas.json'
schema = json.loads(schema_file.read_text())
defs = schema['$defs']
updates = {
    tuple(defs['Cell']['properties']['metric']['enum']): list(specs),
    tuple(defs['NativeSection']['properties']['key']['enum']): sections,
    tuple(defs['Population']['properties']['population_key']['enum']): populations,
    tuple(defs['Axis']['properties']['kind']['enum']): ['edit_error_count'],
}
counts = {key: 0 for key in updates}


def extend(value):
    if isinstance(value, dict):
        if isinstance(value.get('enum'), list):
            key = tuple(value['enum'])
            if key in updates:
                assert not set(value['enum']) & set(updates[key])
                value['enum'].extend(updates[key]); counts[key] += 1
        for child in value.values(): extend(child)
    elif isinstance(value, list):
        for child in value: extend(child)


extend(schema)
assert all(counts.values())
schema_file.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + '\n')
after = {name: sha(DEST / name) for name in before}
after[str(module.relative_to(DEST))] = sha(module)
save('COMMON_PORT_MANIFEST_001.json', after)
save('COMMON_PORT_DELTA_001.json', [{'path': name, 'old_sha256': before.get(name),
    'new_sha256': after[name]} for name in after if before.get(name) != after[name]])
save('METRIC_SPECS_001.json', specs)
save('PREPARATION_RECEIPT_001.json', {'at': datetime.now(timezone.utc).isoformat(),
    'baseline_paths': len(before), 'candidate_paths': len(after), 'new_metrics': len(specs),
    'new_sections': sections, 'new_population_keys': populations,
    'enum_extensions': [{'new_values': updates[key], 'definition_occurrences': count}
                        for key, count in counts.items()],
    'qualification': 'Common parser/sheet ports only. No Cutadapt parser or expanded production pin is implemented yet.'})
print(json.dumps({'candidate_paths': len(after), 'new_metrics': len(specs),
    'new_sections': len(sections), 'new_population_keys': len(populations)}))
