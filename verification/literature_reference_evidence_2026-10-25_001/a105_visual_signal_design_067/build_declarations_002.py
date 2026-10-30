"""Additive design correction; initial001 declarations remain preserved."""
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent


def main():
    d = runpy.run_path(str(HERE / 'build_declarations_001.py'), run_name='design_declarations_only')
    # A genuinely unreadable region can have verified geometry without text.
    d['IMAGE_LOCATOR']['properties']['quote'] = {'type': ['string', 'null']}
    # A single already-normalized ratio/percent does not need a fictitious
    # common raw-signal-scale finding.
    d['visual_selection']['properties']['signal_scale'] = d['obj']({
        'value': d['choice']('supported', 'unknown', 'conflicting', 'not_applicable'),
        'witnesses': d['arr'](d['WITNESS'])})
    # JATS capability failure is not an image-text readability judgment.
    d['row']['properties']['reading_state'] = d['choice'](*d['READING'], 'not_applicable')
    d['row']['properties']['parse_status'] = d['choice']('parsed', 'partial', 'unavailable')
    d['row']['required'].append('parse_status')
    d['RETURN']['items']['properties']['representation_reading_states'] = d['arr'](
        d['choice'](*d['READING'], 'not_applicable'), uniqueItems=True)
    for name, document in [('REQUEST_SCHEMA_002.json', d['REQUEST']),
            ('EXTRACTION_SCHEMA_002.json', d['EXTRACTION']),
            ('SHEET_SCHEMA_002.json', d['SHEET']), ('RETURN_SCHEMA_002.json', d['RETURN'])]:
        with (HERE / name).open('x') as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'final_design_schema_generation': '002', 'schemas_written': 4,
        'initial001_preserved': True, 'application_imports': 0, 'reader_or_calculator_execution': False}))


if __name__ == '__main__':
    main()
