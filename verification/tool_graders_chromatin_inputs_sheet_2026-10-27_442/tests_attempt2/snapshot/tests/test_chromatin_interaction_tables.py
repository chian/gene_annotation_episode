from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np
from gene_annotation_episode.chromatin_interaction_tables import open_chromatin_contact_tables
from gene_annotation_episode.chromatin_interaction_contracts import ChromatinValidationError
from tests.test_chromatin_cooler_inputs import synthetic, request_for, extract, identity
from tests.test_chromatin_interaction_inputs import build_native_sheet


class TablesTest(unittest.TestCase):
    def test_readonly_mmap_repeated_access_and_caller_lifetime(self):
        sheet, memory = build_native_sheet()
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            handles = {}
            for index, (key, stream) in enumerate(memory.items()):
                path = Path(directory) / str(index)
                path.write_bytes(stream.getvalue())
                handles[key] = path.open('rb')
            try:
                with open_chromatin_contact_tables(sheet['data_tables'], streams=handles) as tables:
                    array = tables['populations']['p0']['contacts']
                    self.assertEqual(int(array['value'][2]), 6)
                    self.assertEqual(int(array['value'][2]), 6)
                    self.assertTrue(np.shares_memory(array, array[1:]))
                    with self.assertRaises(ValueError):
                        array['value'][0] = 999
                    with self.assertRaises(TypeError):
                        tables['populations']['new'] = {}
                    del array
                self.assertTrue(all(not stream.closed for stream in handles.values()))
                for stream in handles.values():
                    stream.seek(0)
                    self.assertTrue(stream.read(1))
            finally:
                for stream in handles.values():
                    stream.close()

    def test_hash_and_header_shape_rejected_before_use(self):
        raw = synthetic()
        _, descriptors, streams = extract(raw, request_for(raw))
        key = next(key for key in streams if key.endswith(':contacts'))
        streams[key] = io.BytesIO(streams[key].getvalue() + b'extra')
        with self.assertRaises(ChromatinValidationError), open_chromatin_contact_tables(descriptors, streams=streams):
            pass
        changed = deepcopy(descriptors)
        for descriptor in changed:
            if descriptor['table_key'] == key:
                descriptor['file'] = identity(streams[key].getvalue(), descriptor['file']['format'])
        with self.assertRaises(ChromatinValidationError), open_chromatin_contact_tables(changed, streams=streams):
            pass

    def test_unprovided_or_extra_streams_not_resolved(self):
        raw = synthetic()
        _, descriptors, streams = extract(raw, request_for(raw))
        with self.assertRaises(ChromatinValidationError), open_chromatin_contact_tables(descriptors, streams={}):
            pass
        streams['unselected'] = io.BytesIO()
        with self.assertRaises(ChromatinValidationError), open_chromatin_contact_tables(descriptors, streams=streams):
            pass
