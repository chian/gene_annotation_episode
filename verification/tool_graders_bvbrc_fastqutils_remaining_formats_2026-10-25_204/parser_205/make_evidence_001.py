"""Write filled parser examples and saved-sheet components without acquisition."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
CANDIDATE = WORK / 'candidate'
sys.path.insert(0, str(CANDIDATE))

from gene_annotation_episode.bvbrc_fastqutils_cutadapt_reader import append_cutadapt_report
from gene_annotation_episode.bvbrc_fastqutils_fastqc_reader import _Report
from gene_annotation_episode.bvbrc_fastqutils_trim_reader import parse_trim_galore_report
from gene_annotation_episode.bvbrc_fastqutils_contracts import json_sha256
from gene_annotation_episode.bvbrc_fastqutils_metadata import extract_fastqutils_metadata
from gene_annotation_episode.bvbrc_fastqutils_sheet import populate_fastqutils_sheet
from gene_annotation_episode.bvbrc_fastqutils_calculators import calculate_fastqutils

OUT = HERE / 'evidence_001'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def binding(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(WORK)), sha256=sha256(raw).hexdigest(), byte_count=len(raw))


def context(raw, name):
    return dict(analysis_id='cutadapt_parser_205', document_id='report', task_ref='task:synthetic',
        content=dict(source_ref='source:synthetic', artifact_field='artifact_ref', artifact_ref='content:synthetic',
                     sha256=sha256(raw).hexdigest(), byte_count=len(raw)),
        native_name=name, declared_format='trim_galore_report_0_6_10', producer_version='0.6.10',
        transfer_scope='complete', identity='source_executed_synthetic')


def save_calculation(doc, case):
    template = json.loads((CANDIDATE / 'tests/fixtures/bvbrc_fastqutils/reports/saved_native_sheet.json').read_text())
    original = template['original_task']
    original['submission_receipt_ref'] = doc['artifact']['task_ref']
    metadata = extract_fastqutils_metadata(original, analysis_id=doc['analysis_id'],
        metadata_bindings=[], supplied_values=[], documents=[doc])
    resolution = dict(document_id='report', selection=dict(kind='possessed_content', content=doc['artifact']['content_binding']),
        state='available', matched_contents=[doc['artifact']['content_binding']], artifact_ref=doc['artifact']['id'],
        requirement_refs=[], diagnostic_codes=[])
    sheet = populate_fastqutils_sheet([doc], metadata=metadata, document_resolutions=[resolution])
    before = next(c for c in doc['cells'] if c['metric'] == 'cutadapt_processed_bases' and c['axis']['kind'] == 'none')
    after = next(c for c in doc['cells'] if c['metric'] == 'cutadapt_written_bases' and c['axis']['kind'] == 'none')
    edge = next(e for e in doc['native_lineage'] if e['before_population_ref'] == before['population_ref'])
    job = dict(calculation_id='base_retention', method='retention_v1', state='ready',
        population_refs=[before['population_ref'], after['population_ref']],
        operand_measurement_refs=[before['id'], after['id']], comparison_kind='base_retention', quality_thresholds=[],
        read_key_rule=None, lineage_ref=edge['id'], lineage_basis=dict(basis='native_report', metadata_id=None,
            evidence=None, declaration=None, native_lineage_ref=edge['id']), requirement_refs=[], diagnostic_codes=[])
    parameters = dict(version='fastqutils_calculators_v2', analysis_id=sheet['analysis_id'], calculations=[job])
    components = calculate_fastqutils(sheet, parameters=parameters)
    write(OUT / case / 'sheet.json', sheet)
    write(OUT / case / 'components.json', components)
    return dict(parameter_sha256=json_sha256(parameters), values={r['metric']: dict(value=r['value'], state=r['state'],
        numerator=r['numerator'], denominator=r['denominator']) for r in components['components']})


def main():
    OUT.mkdir(exist_ok=False)
    cases = []
    for base in (WORK / 'native_examples_001', HERE / 'native_examples_001', HERE / 'native_examples_002', HERE / 'native_examples_003'):
        for directory in sorted(base.iterdir()):
            if not directory.is_dir():
                continue
            native_path = directory / ('synthetic.fastq_trimming_report.txt' if directory.name == 'trimgalore_single' else 'stdout.log')
            if not native_path.is_file():
                continue
            raw = native_path.read_bytes()
            ctx = context(raw, native_path.name)
            if directory.name == 'trimgalore_single':
                doc = parse_trim_galore_report(raw, context=ctx)
            else:
                report = _Report(raw, ctx, 'trim_galore_report_0_6_10', 'Trim Galore')
                append_cutadapt_report(report, raw, start=0, end=len(raw))
                doc = report.finish()
            write(OUT / directory.name / 'native_document.json', doc)
            case = dict(case=directory.name, native=binding(native_path), receipt=binding(directory / 'receipt.json'),
                parse_scope=doc['parse_scope'], cell_count=len(doc['cells']), population_count=len(doc['populations']),
                lineage_count=len(doc['native_lineage']), diagnostic_codes=sorted({d['code'] for d in doc['diagnostics']}))
            if directory.name in ('cutadapt_single', 'cutadapt_filtered', 'zero_bases'):
                case['calculation'] = save_calculation(doc, directory.name)
            cases.append(case)
    owned = [CANDIDATE / 'gene_annotation_episode/bvbrc_fastqutils_cutadapt_reader.py',
             CANDIDATE / 'tests/test_bvbrc_fastqutils_cutadapt_reader.py']
    sources = [WORK / 'sources/cutadapt_v4_9/src/cutadapt/report.py', WORK / 'sources/cutadapt_v4_9/src/cutadapt/cli.py']
    generated = [binding(p) for p in sorted(OUT.rglob('*')) if p.is_file()]
    manifest = dict(recorded_at=datetime.now(timezone.utc).isoformat(), workload='CUTADAPT_WORKLOAD_001.md',
        owned_files=[binding(p) for p in owned], native_sources=[binding(p) for p in sources],
        actual_producer_cases=cases, generated=generated,
        scope='Isolated parser and numerical saved-sheet evidence only. No deployed BV-BRC service or complete episode path claim.',
        unchanged_frozen_history='198 and all earlier receipts were read only.',
        remaining=['Other Cutadapt versions are unsupported.', 'Remote BV-BRC producer/version and authenticated artifact execution remain unverified.',
                   'Native discard-option runs omit the named discard counters; those two labels are source-grammar fixture tests.',
                   'Root owns provider/episode integration, source closure pin, packaging and promotion.'])
    write(OUT / 'manifest.json', manifest)
    print(json.dumps(dict(cases=len(cases), owned_files=manifest['owned_files'], generated_bytes=sum(p['byte_count'] for p in generated)), indent=2))


if __name__ == '__main__':
    main()
