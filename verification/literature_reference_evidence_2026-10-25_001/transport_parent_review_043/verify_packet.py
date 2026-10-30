"""Mechanical reproduction of the already read043 packet after root reset.

No new scientific source interpretation, image transcription or native episode.
"""
import hashlib
import json
from pathlib import Path
import runpy

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ROOT = OUT.parents[2]
OWNER = BASE / 'a105_transport_case_043'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((OWNER / 'MANIFEST.json').read_bytes())
    original = {p.relative_to(OWNER).as_posix(): digest(p) for p in OWNER.rglob('*') if p.is_file()}
    for row in manifest['files']:
        path = OWNER / row['path']
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], row['path']
    reset = json.loads((BASE / 'transport_parent_reset_043/READ_RECEIPT.json').read_bytes())
    assert reset['complete'] and len(reset['acknowledged_chunks']) == reset['chunks_total'] == 38
    for row in reset['documents']:
        assert Path(row['path']).stat().st_size == row['bytes'] and digest(Path(row['path'])) == row['sha256']
    destination = OUT / 'reproduced_001'
    destination.mkdir(exist_ok=False)
    script = (OWNER / 'check_arithmetic.py').read_text()
    old = 'O=Path(__file__).resolve().parent'
    assert script.count(old) == 1
    script = script.replace(old, 'O=Path(__file__).resolve().parent / "reproduced_001"')
    old_source = "p=O/'source/PMC5738728_retained_primary.txt'"
    assert script.count(old_source) == 1
    script = script.replace(old_source, "p=Path(" + repr(str(OWNER / 'source/PMC5738728_retained_primary.txt')) + ')')
    reproduction = OUT / 'reproduce_arithmetic_001.py'
    with reproduction.open('x') as stream:
        stream.write(script)
    runpy.run_path(str(reproduction), run_name='__main__')
    for name in ('NUMERICAL_CASE.json', 'SOURCE_LOCATORS.json'):
        assert (destination / name).read_bytes() == (OWNER / name).read_bytes(), name
    assert original == {p.relative_to(OWNER).as_posix(): digest(p) for p in OWNER.rglob('*') if p.is_file()}
    additional = {'source_case': 'Previously read043 retained packet; no fresh primary-source claim',
        'cold_pyruvate_uM': 1000, 'tracer_pyruvate_uM': 10, 'total_pyruvate_uM': 1000 + 10,
        'nominal_tracer_fraction': 10 / (1000 + 10), 'formula': 'labeled/(cold+labeled)',
        'interpretation': 'Exposure denominator only; no inhibition, isotope recovery, transport flux or specificity inferred',
        'nominal_proton_activity_ratio_name': 'pH-derived activity ratio; a concentration ratio additionally needs activity-coefficient assumptions',
        'original_packet_key_preserved': 'nominal_proton_concentration_ratio',
        'original_packet_value_and_meaning_preserved': True}
    with (OUT / 'ADDITIONAL_EXPOSURE_ARITHMETIC_001.json').open('x') as stream:
        json.dump(additional, stream, indent=2)
        stream.write('\n')
    receipt = {'passed': True, 'manifest_entries_verified': len(manifest['files']),
        'original_case_files_unchanged': len(original), 'reproduced_json_files_exact': 2,
        'full_post_packet_reset_chunks': 38, 'full_post_packet_reset_entries': len(reset['documents']),
        'full_post_packet_reset_bytes': sum(row['bytes'] for row in reset['documents']),
        'original_manifest_sha256': digest(OWNER / 'MANIFEST.json'),
        'packet_scientific_interpretation_before_reset': False,
        'scope': 'Packet integrity, existing pure arithmetic and source-locator byte matching only',
        'fresh_primary_article_or_figure_read_by_parent': False, 'native_episode_or_model_run': False,
        'synthetic_controller_observations': 0, 'annotation_credit': None, 'goal_complete': False}
    with (OUT / 'RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
