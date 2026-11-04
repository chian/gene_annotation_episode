from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from gene_annotation_episode.chromatin_interaction_contracts import (
    ChromatinValidationError, chromatin_record_schema, validate_chromatin_record,
    decode_chromatin_json, chromatin_record_digest,
)


def examples():
    path = Path.cwd() / 'WORKED_RECORDS.json'
    return {row['example_key']: row['record'] for row in json.loads(path.read_text())['records']}


class ContractsTest(unittest.TestCase):
    def test_independent_local_root_and_all_scientific_records(self):
        rows = json.loads((Path.cwd() / 'WORKED_RECORDS.json').read_text())['records']
        count = 0
        for row in rows:
            if row['schema_definition'] == 'PopulationSeal':
                continue  # Additive 441/003 requires native, absent in historical439 seal.
            with self.subTest(example=row['example_key']):
                schema = chromatin_record_schema(row['schema_definition'])
                Draft202012Validator.check_schema(schema)
                validate_chromatin_record(row['schema_definition'], row['record'])
                self.assertEqual(schema['$ref'], '#/$defs/' + row['schema_definition'])
                count += 1
        self.assertGreater(count, 60)
        schema = chromatin_record_schema('PopulationSpec')
        schema['$defs']['PopulationSpec']['properties'].clear()
        self.assertIn('population_key', chromatin_record_schema('PopulationSpec')['$defs']['PopulationSpec']['properties'])
        self.assertEqual(set(chromatin_record_schema('PopulationSpec')['$defs']), {'PopulationSpec'})

    def test_reject_unknown_bool_float_integer_nonfinite_duplicate(self):
        sample = {'population_key': 'p0', 'chromosome': 'chrA', 'start_bp': 0, 'end_bp': 10}
        for update in ({'start_bp': True}, {'start_bp': 0.0}, {'end_bp': float('inf')}, {'extra': 3}, {'end_bp': 0}):
            with self.subTest(update=update), self.assertRaises(ChromatinValidationError):
                validate_chromatin_record('PopulationSpec', sample | update)
        for encoded in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}'):
            with self.assertRaises(ChromatinValidationError):
                decode_chromatin_json(encoded)
        with self.assertRaises(ChromatinValidationError):
            chromatin_record_schema('not_a_record')

    def test_record_copy_and_digest(self):
        row = examples()['raw.sheet']
        copied = validate_chromatin_record('ContactSheet', row)
        self.assertEqual(row, copied)
        self.assertEqual(chromatin_record_digest(row), chromatin_record_digest(copied))
        copied['failures'].append({})
        self.assertFalse(row['failures'])
