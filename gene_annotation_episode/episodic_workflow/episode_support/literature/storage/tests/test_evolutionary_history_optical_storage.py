"""The optical rate repository on the custody-scoped store: population from a source that quotes the NADH slope,
blank, extinction coefficient and path length, the saved sheet read back and its cells projected."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_optical_storage:LiteratureOpticalRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
TEXT = ('Synthetic sample NADH slope -0.012 AU/min; blank -0.002 AU/min; epsilon 5000 M^-1 cm^-1; path 10 mm; '
        'wavelength 340 nm. Matched no-reaction background, same endpoint and interval, supported initial rate. '
        'A single unnamed preparation of construct X.')


def selection(reference):
    def witness(quote, occurrence=0):
        start = -1
        for _ in range(occurrence + 1):
            start = TEXT.index(quote, start + 1)
        return {'source_ref': reference, 'representation': 'original', 'start': len(TEXT[:start].encode()),
                'end': len(TEXT[:start + len(quote)].encode()), 'quote': quote}

    def meaning(value, quote=None):
        return {'value': value, 'witnesses': [] if value == 'unknown' else [witness(quote or TEXT)]}

    def quantity(quote, number, unit):
        start = quote.index(number)
        unit_occurrence = TEXT[:TEXT.index(quote)].count(unit)
        return {'measurement_identity': None, 'condition': None, 'measured_entity': None, 'interval': None,
                'measurement': {'number': {'witness': witness(quote), 'number_start': start,
                                           'number_end': start + len(number)},
                                'unit': witness(unit, unit_occurrence)},
                'qualification': meaning('reported_point', quote)}
    return {'source_ref': reference, 'source_kind': 'synthetic_fixture', 'molecule': None, 'construct': None,
            'preparation': None, 'condition': None, 'measured_entity': None,
            'signal_kind': meaning('absorbance_slope'),
            'signals': {'sample': quantity('-0.012 AU/min', '-0.012', 'AU/min'),
                        'blank': quantity('-0.002 AU/min', '-0.002', 'AU/min')},
            'calibration': {'epsilon': quantity('5000 M^-1 cm^-1', '5000', 'M^-1 cm^-1'),
                            'path_length': quantity('10 mm', '10', 'mm'),
                            'wavelength': quantity('340 nm', '340', 'nm')},
            'relation': meaning('applicable_extinction_relation'),
            'blank_role': meaning('matched_no_reaction_background'), 'same_endpoint': meaning('same'),
            'matched_window': meaning('same'), 'rate_window': meaning('source_supported_rate_interval'),
            'covariance_source_ref': None}


def test_an_optical_sheet_is_saved_read_back_and_projected(world):
    reference, artifact = source(world, TEXT, 'text/plain')
    populated, listed, saved, cells = run(world, 'optical', [
        call(REPOSITORY, 'populate', selection(reference), scope=world['scope']),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET])], held=[reference, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and listed == [sheet]
    assert saved['input_source_ref'] == reference
    assert {row['sheet_ref'] for row in cells} == {sheet}
    rate = next(row for row in cells if row['component'] == 'net_rate')
    assert rate['value'] == 2.0 and rate['status'] == 'populated'
