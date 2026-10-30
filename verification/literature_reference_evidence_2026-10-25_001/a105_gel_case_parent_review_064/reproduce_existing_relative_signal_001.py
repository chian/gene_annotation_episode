"""One cached-primary case through existing pure readers, no runtime publication.

Root selected the experiment/meanings after its full primary/reset review.
Image numerals are attributed visual transcriptions, not OCR or densitometry.
Local content handles below do not assert installed Store records or receipt.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PIN = BASE / 'a105_contract_information_design_059/connected_stage_004/pin_010'
sys.path.insert(0, str(PIN))

from gene_annotation_episode.literature_binding_visual_inputs import _Inputs
from gene_annotation_episode.literature_prose_reader import _direct_paragraph_text, _tag
from gene_annotation_episode.literature_ratio_calculations import populate_relative_signal
from gene_annotation_episode.literature_ratio_reader import read_jats_relative_percent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def emit(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    reset = json.loads((HERE / 'source_review_001/RESET_READ_RECEIPT_001.json').read_text())
    assert reset['status'] == 'complete root post-paper reset before own component conversion'
    out = HERE / 'existing_relative_signal_001'
    out.mkdir()
    xml_path = BASE / 'primary_yeag/PMC4664914_original.xml'
    image_path = BASE / 'primary_yeag/srep17524-f3.jpg'
    xml_bytes, image_bytes = xml_path.read_bytes(), image_path.read_bytes()
    assert digest(xml_bytes) == '71d33026f2a245e7c302e7449f9f28c1711f812cddbdc8c9b9fc74657064a9c4'
    xml = xml_bytes.decode('utf-8')
    root = ET.fromstring(xml)
    matching = []
    for section in root.iter():
        if _tag(section) != 'sec':
            continue
        paragraphs = [child for child in section if _tag(child) == 'p']
        for index, paragraph in enumerate(paragraphs):
            text = _direct_paragraph_text(paragraph)
            if 'mutant variants were produced at' in text and all(name in text for name in ('K116A', 'R232A', 'K426A', 'Y382stop')):
                matching.append((section.get('id'), index))
    assert len(matching) == 1, matching
    section_id, paragraph_index = matching[0]
    xml_ref, image_ref = '@primary_yeag_xml', '@original_yeag_fig3'
    xml_artifact = 'artifact_' + digest(xml_bytes)
    image_artifact = 'artifact_' + digest(image_bytes)
    calls = []
    def source(reference, representation):
        calls.append((reference, representation))
        assert reference == image_ref and representation == 'original'
        return {'artifact_ref': image_artifact, 'content': image_bytes}
    inputs = _Inputs(source)
    image = inputs.image({'image_id': 'fig3', 'source_ref': image_ref,
                          'original_source_ref': image_ref, 'mapping': None})
    assert image['error'] is None and (image['width'], image['height']) == (787, 557)
    # These exact label nominations follow root's original-image view; helper
    # validation checks only actual source bytes/geometry, never numeral truth.
    visual = {
        'K116A': ('0.64', [144, 537, 179, 557], [95, 537, 125, 557], 'left_blot_WT_lane1'),
        'R232A': ('0.48', [195, 537, 228, 557], [95, 537, 125, 557], 'left_blot_WT_lane1'),
        'K426A': ('1.12', [532, 537, 567, 557], [489, 537, 518, 557], 'right_blot_WT_lane1'),
        'Y382stop': ('0.96', [584, 537, 619, 557], [489, 537, 518, 557], 'right_blot_WT_lane1')}
    expected = {'K116A': .64, 'R232A': .48, 'K426A': 1., 'Y382stop': .96}
    rows, cases = [], {}
    for variant, (label, region, reference_region, owner) in visual.items():
        parsed = read_jats_relative_percent({'source_ref': xml_ref, 'artifact_ref': xml_artifact,
            'xml': xml, 'representation': 'primary_jats'}, section_id=section_id,
            paragraph_index=paragraph_index, expected_subject='YeaG', variant=variant,
            reference_literal='wild-type levels')
        assert parsed['observations'][0]['value'] == expected[variant]
        nominated = {'version': 'relative_visual_signal_v1', 'subject': 'YeaG',
            'variant': variant, 'reference': 'wild-type levels', 'observations': [{
                'printed_label': label, 'reference_printed_label': '1.0',
                'original_source_ref': image_ref, 'original_artifact_ref': image_artifact,
                'image_region': region, 'reference_image_region': reference_region}]}
        visual_path = out / ('VISUAL_' + variant + '_001.json')
        emit(visual_path, nominated)
        encoded = visual_path.read_bytes()
        witnesses = [inputs.witness({'kind': 'image', 'image_id': 'fig3', 'region': box, 'quote': quote})
                     for box, quote in ((region, label), (reference_region, '1.0'))]
        assert all(w['error'] is None and w['authentication'] == 'image_bytes_and_geometry_only' for w in witnesses)
        observation = {'value': float(label) / 1., 'origin': 'visual_transcription',
            'uncertainty': {'kind': 'unreported', 'magnitude': None, 'count': None, 'sampling_basis': 'unspecified'},
            'source': {'source_ref': '@local_visual_' + variant, 'artifact_ref': 'artifact_' + digest(encoded),
                'representation': 'retained_visual_transcription', **deepcopy(nominated['observations'][0])}}
        sheet = populate_relative_signal([*parsed['observations'], observation])
        assert all(sheet['cells'][key]['value'] is None for key in ('calibrated_amount_ratio',
            'amount_adjusted_effect', 'source_profile_log_ratio', 'source_signed_index'))
        conflict = variant == 'K426A'
        assert (sheet['cells']['reported_ratio']['status'] == 'conflicting') == conflict
        if conflict:
            assert sheet['cells']['reported_ratio']['value'] is None
            assert sheet['cells']['reported_ratio']['value_candidates'] == [1., 1.12]
        else:
            assert sheet['cells']['reported_ratio']['value'] == expected[variant]
        assert sheet['independent_preparation_count'] is None and sheet['annotation_credit'] is None
        cases[variant] = {'source_text_extraction': parsed, 'visual_nomination': nominated,
            'image_geometry_witnesses': witnesses, 'reference_owner_nomination': owner,
            'reference_owner_qualification': 'same displayed reference within this blot; biological replicate identity/cross-blot relationship unknown',
            'sheet': sheet}
        rows.append({'variant': variant, 'reported_ratio': sheet['cells']['reported_ratio']['value'],
            'ratio_candidates': sheet['cells']['reported_ratio']['value_candidates'],
            'difference': sheet['cells']['difference_from_reference']['value'],
            'log_ratio': sheet['cells']['log_reported_ratio']['value'],
            'source_text_ratio': expected[variant], 'printed_image_ratio': label,
            'exact_image_ratio': str(Fraction(label)), 'exact_image_difference': str(Fraction(label) - 1)})
    emit(out / 'ACTUAL_SOURCE_COMPONENTS_001.json', cases)
    modules = {}
    for name, module in tuple(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN.resolve()), (name, str(path))
            modules[name] = {'path': str(path.relative_to(PIN.resolve())), 'sha256': digest(path.read_bytes())}
    receipt = {'scope': 'Cached-primary pure source reader + separate existing calculator; root scientific/visual nominations. No Store/runtime/model/native operation or typed delivery.',
        'source_xml': {'path': str(xml_path), 'sha256': digest(xml_bytes)},
        'original_image': {'path': str(image_path), 'sha256': digest(image_bytes)},
        'section_id': section_id, 'paragraph_index': paragraph_index, 'rows': rows,
        'image_text_truth': 'root visual transcription; helper authenticates bytes/geometry only; no OCR/densitometry',
        'source_handles': 'local aliases/content-derived artifact handles, not installed or received Store records',
        'actual_source_callbacks': calls, 'project_modules_from_accepted010_pin': modules,
        'new_production_code_or_scoring_policy': False, 'runtime_observations_created': 0,
        'axis_use': 'expression comparability for perturbation/recovery; not direct A105 activity',
        'known_missing': ['blot-specific loading/calibration/exposure/replicate uncertainty',
                          'molecular amount calibration', 'matched-amount functional response',
                          'biological observation and shared-denominator covariance']}
    emit(out / 'RECEIPT_001.json', receipt)
    print(json.dumps({'section_id': section_id, 'paragraph_index': paragraph_index,
                      'actual_cases': len(cases), 'rows': rows, 'runtime_observations': 0,
                      'no_new_reader_implemented': True}))


if __name__ == '__main__':
    main()
