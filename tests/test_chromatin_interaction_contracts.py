import unittest

from gene_annotation_episode.chromatin_interaction_contracts import (
    ChromatinValidationError, chromatin_record_schema, validate_chromatin_record,
    decode_chromatin_json,
)


class ContractsTest(unittest.TestCase):
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
