"""Final association-aware declaration generation; no reader implementation."""
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent


def main():
    d = runpy.run_path(str(HERE / 'build_declarations_001.py'), run_name='design_declarations_only')
    d['IMAGE_LOCATOR']['properties']['quote'] = {'type': ['string', 'null']}
    relation_values = ('supported', 'different', 'unknown', 'conflicting')
    d['RELATION']['properties']['value'] = d['choice'](*relation_values)
    d['visual_selection']['properties']['signal_scale'] = d['obj']({
        'value': d['choice']('supported', 'different', 'unknown', 'conflicting', 'not_applicable'),
        'witnesses': d['arr'](d['WITNESS'])})
    d['row']['properties']['comparison_relation'] = d['extracted_meaning'](d['RELATION'])
    d['row']['properties']['reading_state'] = d['choice'](*d['READING'], 'not_applicable')
    d['row']['properties']['parse_status'] = d['choice']('parsed', 'partial', 'unavailable')
    d['row']['required'].append('parse_status')
    reasons = (*d['REASONS'], 'different_reported_quantities', 'signal_scales_differ')
    d['DIAGNOSTIC']['properties']['code'] = d['choice'](*reasons)
    d['CELL']['properties']['unavailable_reason']['enum'] = [*reasons, None]
    p = d['RETURN']['items']['properties']
    p['unavailable_reason']['enum'] = [*reasons, None]
    p['representation_reading_states'] = d['arr'](d['choice'](*d['READING'], 'not_applicable'), uniqueItems=True)
    p['comparison_relation_states'] = d['arr'](d['choice'](*relation_values), uniqueItems=True)
    p['signal_scale_states'] = d['arr'](d['choice']('supported', 'different', 'unknown', 'conflicting', 'not_applicable'), uniqueItems=True)
    p['signal_use'] = d['choice']('experimental_comparability', 'measured_endpoint', 'other', 'unknown', 'conflicting')
    p['meaning_statuses'] = d['obj']({name: d['choice']('known', 'unknown', 'conflicting') for name in d['COMPARISON_FIELDS']})
    p['physical_identity_states'] = d['arr'](d['choice']('known', 'unknown', 'conflicting'), uniqueItems=True)
    p['reference_identity_states'] = d['arr'](d['choice']('known', 'unknown', 'conflicting'), uniqueItems=True)
    p['uncertainty_kind'] = {'const': 'unknown'}
    p['uncertainty_evaluation'] = {'const': 'numeric_uncertainty_reader_unimplemented'}
    d['RETURN']['items']['required'] = list(p)
    for name, document in [('REQUEST_SCHEMA_004.json', d['REQUEST']),
            ('EXTRACTION_SCHEMA_004.json', d['EXTRACTION']),
            ('SHEET_SCHEMA_004.json', d['SHEET']), ('RETURN_SCHEMA_004.json', d['RETURN'])]:
        with (HERE / name).open('x') as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'final_design_schema_generation': '004', 'schemas_written': 4,
        'prior001_002_003_preserved': True, 'application_imports': 0, 'reader_or_calculator_execution': False}))


if __name__ == '__main__':
    main()
