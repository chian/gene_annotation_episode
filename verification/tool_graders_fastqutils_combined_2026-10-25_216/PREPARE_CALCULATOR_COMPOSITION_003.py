"""Preserve the verified parser tree and prepare its next integration tree."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'candidate_002'
TARGET = HERE / 'candidate_003'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


if __name__ == '__main__':
    assert not TARGET.exists()
    manifest = json.loads((HERE / 'parser_checks_001/source_after.json').read_text())
    receipt = json.loads((HERE / 'parser_checks_001/receipt.json').read_text())
    assert receipt['passed'] and not receipt['changed_sources'] and len(manifest) == 1162
    for name, expected in manifest.items():
        raw = (SOURCE / name).read_bytes()
        assert sha(raw) == expected, name
        destination = TARGET / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)

    info = TARGET / 'gene_annotation_episode/bvbrc_fastqutils_tool_info.py'
    text = info.read_text()
    samstat = ('SAMstat2.2.3 legacy HTML and2.5.0 HTML have different native statistics and '
        'alignment-flag exclusions. Preserve the actual producer version, reported alignment '
        'record populations, mate strata, counts, quality summaries and uncertainty. Legacy '
        'embedded arrays retain their coordinate labels, density or clustered-mean meanings '
        'and native defects; current SVG plots do not expose their original numerical arrays. '
        'Do not reconstruct those arrays from graph geometry. A rounded display remains rounded. '
        'A closed HTML report does not establish that all original input records were processed. '
        'The recognized FastqUtils SAMstat failure report carries a failed measurement and '
        'explicit execution-evidence requirement; it is not a zero-result analysis. Unsupported '
        'SAMstat versions, other Cutadapt versions and other SRA formats remain retained '
        'artifacts with explicit parser requirements until their formats are implemented.')
    text = replace_once(text,
        'Unsupported SAMstat, other Cutadapt versions and other SRA formats remain retained '
        'artifacts with explicit parser requirements until their formats are implemented.', samstat)
    text = replace_once(text,
        'Mapping fractions require the complete input-read denominator and unambiguous actual read-segment correspondence.',
        'Fractions of original input reads require the complete input-read denominator and '
        'unambiguous actual read-segment correspondence.')
    mapping = ('SAMstat report-bin calculations are separate from original-read mapping. '
        'Select samstat_report_mapping_v1 with the report-wide population, one reported mate '
        'stratum, or the two explicitly disjoint mate strata from one artifact. They calculate '
        'the mapped-record fraction and native MAPQ-at-least-30-bin fraction among those reported '
        'alignment records. Keep all four bin counts, numerator, denominator and population '
        'qualifications. Do not combine a report-wide total with its mates or sum different '
        'reports. MAPQ255 shares the high native bin but does not establish known mapping '
        'confidence. Unknown original-input coverage remains unknown; an explicit prefix remains '
        'partial. A zero denominator is undefined, missing bins stay missing, and conflicting '
        'counts remain incompatible. ')
    text = replace_once(text, 'Select the numerical components and return fields needed for the assigned question.',
                        mapping + 'Select the numerical components and return fields needed for the assigned question.')
    info.write_text(text)

    after = {name: sha((TARGET / name).read_bytes()) for name in manifest}
    changed = [name for name in manifest if manifest[name] != after[name]]
    assert changed == ['gene_annotation_episode/bvbrc_fastqutils_tool_info.py']
    record = dict(status='prepared_for214_delivery_not_yet_composed_or_verified',
        source='candidate_002', target='candidate_003', copied_paths=len(manifest),
        source_manifest_sha256=sha((HERE / 'parser_checks_001/source_after.json').read_bytes()),
        changed_paths=changed, instruction_additions=[samstat, mapping],
        production_changed=False, calculator214_delivered=False)
    for name, value in [('PREPARED_CALCULATOR_COMPOSITION_003.json', record),
                        ('prepared_source_before_003.json', after)]:
        with (HERE / name).open('x') as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    print(json.dumps(dict(prepared=True, copied_paths=len(manifest), changed_paths=changed,
                          calculator214_delivered=False), sort_keys=True))
