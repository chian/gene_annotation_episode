"""Root reproduction of frozen063 examples and independent mechanical cases.

No primary source, model, Store, episode, controller or scientific score.
Writes only a new root review directory; never reruns owner sealing scripts.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

from PIL import Image
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
DELIVERY = BASE / 'a105_controlled_graph_reader_063'
PIN = DELIVERY / 'pin_003'
sys.path.insert(0, str(PIN))
from gene_annotation_episode import literature_controlled_response_figure_inputs as reader


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def emit(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    output = HERE / 'reader_063_root_proof_001'
    output.mkdir()
    manifest = json.loads((DELIVERY / 'MANIFEST_003.json').read_bytes())
    for row in manifest['entries']:
        raw = (DELIVERY / row['path']).read_bytes()
        assert len(raw) == row['bytes'] and digest(raw) == row['sha256'], row['path']
    pin_manifest = json.loads((DELIVERY / 'PIN_MANIFEST_003.json').read_bytes())
    for row in pin_manifest['files']:
        raw = (PIN / row['path']).read_bytes()
        assert len(raw) == row['bytes'] and digest(raw) == row['sha256'], row['path']
        assert raw == (ROOT / row['path']).read_bytes(), row['path']
    actual_pin_files = {str(p.relative_to(PIN)) for p in PIN.rglob('*') if p.is_file()}
    assert actual_pin_files == {r['path'] for r in pin_manifest['files']}
    # The additive patch contains exactly two NEW file hunks, with no context
    # or deletions. Reconstruct the complete files independently without git.
    reconstructed, target, body = {}, None, []
    for line in (DELIVERY / 'IMPLEMENTATION_003.patch').read_text().splitlines(keepends=True):
        if line.startswith('--- '):
            if target is not None:
                reconstructed[target] = ''.join(body).encode()
            assert line.strip() == '--- /dev/null'
            target, body = None, []
        elif line.startswith('+++ b/'):
            target = line[len('+++ b/'):].strip()
        elif line.startswith('@@ '):
            assert line.startswith('@@ -0,0 +1,')
        else:
            assert line.startswith('+') and target is not None
            body.append(line[1:])
    reconstructed[target] = ''.join(body).encode()
    assert set(reconstructed) == {
        'gene_annotation_episode/literature_controlled_response_figure_inputs.py',
        'tests/test_literature_controlled_response_figure_inputs.py'}
    for name, raw in reconstructed.items():
        assert raw == (PIN / name).read_bytes()
    declarations = PIN / 'verification/literature_reference_evidence_2026-10-25_001/a105_controlled_graph_design_061'
    request = Draft202012Validator(json.loads((declarations / 'GRAPH_REQUEST_SCHEMA_001.json').read_text()))
    result_schema = Draft202012Validator(json.loads((declarations / 'GRAPH_RESULT_SCHEMA_002.json').read_text()))
    reproductions = []
    for folder in sorted((DELIVERY / 'examples_003').iterdir()):
        arguments = json.loads((folder / 'REQUEST.json').read_bytes())
        selected = json.loads((folder / 'SOURCES.json').read_bytes())
        sources = {}
        for row in selected:
            raw = (folder / row['file']).read_bytes()
            assert digest(raw) == row['sha256']
            sources[row['source_ref'], row['representation']] = {'artifact_ref': row['artifact_ref'], 'content': raw}
        calls = []
        def read(ref, representation):
            calls.append([ref, representation])
            return sources[ref, representation]
        request.validate(arguments)
        actual = reader.read_controlled_response_rate_figure(arguments, read_source=read)
        result_schema.validate(actual)
        assert actual == json.loads((folder / 'ACTUAL_RESULT.json').read_bytes()), folder.name
        emit(output / (folder.name + '_REPRODUCED.json'), actual)
        reproductions.append({'example': folder.name, 'calls': calls, 'operand': actual['operand_projection']})
    # A new geometry and scale, independently chosen rather than copied from
    # the owner's expected-number fixtures: y20=>100, y100=>20 nmol/min.
    template = json.loads((DELIVERY / 'examples_003/negative_lower/REQUEST.json').read_bytes())
    image_ref = template['images'][0]['source_ref']
    text_ref = template['measurement']['axis']['unit']['candidates'][0]['source_ref']
    with Image.new('RGB', (40, 120), 'white') as image:
        for y in range(31, 70):
            for x in range(12, 26):
                image.putpixel((x, y), (0, 0, 0))
        encoded = BytesIO(); image.save(encoded, format='PNG'); image_bytes = encoded.getvalue()
    text = b'<td>100</td><td>20</td><td>nmol/min</td><td>linear axis</td>'
    def witness(quote):
        start = text.index(b'<td>' + quote.encode() + b'</td>') + 4
        return {'kind': 'text', 'source_ref': text_ref, 'representation': 'text',
                'start': start, 'end': start + len(quote.encode()), 'quote': quote}
    def literal(quote):
        return {'status': 'exact', 'candidates': [witness(quote)], 'fragments': []}
    selection = deepcopy(template)
    measurement = selection['measurement']
    measurement['bar_selection']['roi'] = {'left': 12, 'top': 1, 'right': 26, 'bottom': 119}
    measurement['axis']['first'] = {'pixel': 20, 'tick': literal('100')}
    measurement['axis']['second'] = {'pixel': 100, 'tick': literal('20')}
    measurement['axis']['unit'] = literal('nmol/min')
    measurement['axis']['scale']['witnesses'] = [witness('linear axis')]
    sources = {(image_ref, 'original'): {'artifact_ref': 'artifact_' + digest(image_bytes), 'content': image_bytes},
               (text_ref, 'text'): {'artifact_ref': 'artifact_' + digest(text), 'content': text}}
    request.validate(selection)
    own = reader.read_controlled_response_rate_figure(selection, read_source=lambda *key: sources[key])
    result_schema.validate(own)
    assert own['operand_projection']['value'] == 50.5
    assert own['operand_projection']['unit'] == 'nmol/min'
    assert own['operand_projection']['digitization_interval'] == {'lower': 49.5, 'upper': 51.5}
    exact = own['measurement']['pixel_result']['native_ordinate']
    assert Fraction(int(exact['numerator']), int(exact['denominator'])) == Fraction(101, 2)
    emit(output / 'INDEPENDENT_REQUEST.json', selection)
    emit(output / 'INDEPENDENT_RESULT.json', own)
    # Probe the open review question. This intentionally dishonest callback is
    # outside Store's content-addressed resolver. The pure reader preserves
    # both byte hashes but does not cross-check duplicate artifact handles.
    inconsistent = deepcopy(sources)
    inconsistent[text_ref, 'text']['artifact_ref'] = inconsistent[image_ref, 'original']['artifact_ref']
    collision = reader.read_controlled_response_rate_figure(selection, read_source=lambda *key: inconsistent[key])
    result_schema.validate(collision)
    assert collision['operand_projection']['value'] == 50.5
    emit(output / 'CALLBACK_CONSISTENCY_PROBE.json', collision)
    imports = []
    for name, module in tuple(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN.resolve()), (name, str(path))
            imports.append({'module': name, 'path': str(path.relative_to(PIN)), 'sha256': digest(path.read_bytes())})
    receipt = {'sealed_payloads_verified': len(manifest['entries']), 'pin_files_verified': len(pin_manifest['files']),
        'pin_has_no_extra_files': True, 'root_and_pin_files_identical': len(pin_manifest['files']),
        'new_files_independently_reconstructed': len(reconstructed), 'examples_exactly_reproduced': reproductions,
        'independent_constructed_case': own['operand_projection'], 'actual_project_imports': imports,
        'callback_consistency_probe': 'same artifact handle/different bytes accepted; actual SHA256s retained. Caller custody precondition; future native adapter must bind Store.get_artifact and prohibit arbitrary resolver records.',
        'tests_reviewed': 'all721 lines; owner frozen terminal134passed. This proof does not rerun that suite.',
        'scope': 'constructed pixels and labels only; no primary paper, runtime persistence, model, typed delivery or scientific score',
        'scientific_model_calls': 0, 'runtime_observations': 0}
    emit(output / 'ROOT_RECEIPT_001.json', receipt)
    print(json.dumps({'payloads': len(manifest['entries']), 'pin_files': len(pin_manifest['files']),
        'exact_example_reproductions': len(reproductions), 'independent_value': 50.5,
        'actual_pin_imports': len(imports), 'callback_consistency_precondition_explicit': True}))


if __name__ == '__main__':
    main()
