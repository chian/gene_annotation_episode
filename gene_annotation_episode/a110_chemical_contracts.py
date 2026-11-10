"""A110 declared chemical panel formats, separate from expression evidence."""
from .component_axis_native_contracts import obj, text, nullable, array, identities


VERSION = 'a110_chemical_accounting_v2'


def source_schema():
    species = obj({'id': text(), 'entity_id': nullable(text()), 'compartment': nullable(text()),
        'kind': {'enum': ['chemical', 'electron', 'unknown']}, 'formula': nullable(text()),
        'charge': nullable({'type': 'integer'}), 'source_locator': text()})
    participant = obj({'species_id': text(), 'coefficient': text(), 'source_locator': text()})
    conditions = obj({'key': text(), 'temperature_kelvin': nullable({'type': 'number', 'exclusiveMinimum': 0}),
        'description': text(), 'source_locator': text()})
    gibbs = obj({'value_kj_per_mol': {'type': 'number'},
        'convention': {'enum': ['chemical', 'biochemical_transformed', 'unknown']},
        'conditions': conditions, 'source_locator': text()})
    reaction = obj({'id': text(), 'entity_id': nullable(text()),
        'participants': array(participant, minimum=1), 'source_locator': text(),
        'standard_gibbs': nullable(gibbs), 'conditions': nullable(conditions),
        'activities': array(obj({'species_id': text(),
            'value': nullable({'type': 'number', 'exclusiveMinimum': 0}),
            'unit': {'const': 'dimensionless_activity'}, 'source_locator': text()}))})
    pool = obj({'id': text(), 'members': array(obj({'species_id': text(),
        'carrier_units': text(), 'source_locator': text()}), minimum=1),
        'members_complete': {'type': 'boolean'}, 'source_locator': text()})
    return obj({'version': {'const': 'a110_chemical_panel_v1'},
        'dataset_id': nullable(text()), 'origin': {'enum': ['reported', 'retained_extraction', 'synthetic']},
        'species': array(species, minimum=1), 'reactions': array(reaction, minimum=1),
        'pathway': array(obj({'reaction_id': text(), 'multiplier': text(), 'source_locator': text()})),
        'carrier_pools': array(pool), 'reported_constraints': nullable({'type': 'object'})})


def selection_schema():
    return obj({'reaction_ids': {**identities(), 'minItems': 1},
        'include_declared_pathway': {'type': 'boolean'},
        'include_reported_constraints': {'type': 'boolean'}})
