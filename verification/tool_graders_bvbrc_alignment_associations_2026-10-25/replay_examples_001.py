"""Read saved operands once, then replay with I/O/network/subprocess forbidden."""
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch
from contextlib import ExitStack

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode import bvbrc_alignment_provider_contracts as ac
from gene_annotation_episode import bvbrc_metacats_association_contracts as mc
from gene_annotation_episode.bvbrc_alignment_associations import extract_alignment_associations, extract_inline_fasta_members
from gene_annotation_episode.bvbrc_metacats_associations import extract_metacats_associations
from gene_annotation_episode.bvbrc_metacats_biological_calculators import biological_group_counts
from gene_annotation_episode.bvbrc_msa_calculators import msa_native_entropy, msa_reference_differences

manifest = json.loads((OUT / 'EXAMPLE_MANIFEST_001.json').read_text())
examples = []
for entry in manifest['examples']:
    raw = (ROOT / entry['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    examples.append(json.loads(raw))


def forbidden(*args, **kwargs):
    raise AssertionError('I/O, network or subprocess attempted during serialized replay')


counts = {'serialized_examples': 0, 'common_validations': 0, 'metacats_validations': 0, 'calculations': 0,
    'invalid_common_results': 0, 'invalid_metacats_results': 0, 'inline_replays': 0}
with ExitStack() as stack:
    for owner, names in [(builtins, ['open']), (io, ['open']),
            (Path, ['open', 'read_text', 'read_bytes', 'write_text', 'write_bytes']),
            (os, ['open', 'read', 'write', 'stat', 'lstat', 'listdir', 'scandir', 'system', 'popen']),
            (socket, ['socket', 'create_connection', 'getaddrinfo']),
            (subprocess, ['Popen', 'run', 'call', 'check_call', 'check_output'])]:
        for name in names:
            stack.enter_context(patch.object(owner, name, forbidden))
    for example in examples:
        operands = example['common_operands']; value = example['common_result']['value']
        assert extract_alignment_associations(**operands) == example['common_result'], example['name']
        if value is not None:
            assert ac.validate_association_set(value, inputs=operands['inputs'], documents=operands['documents']) == value
            counts['common_validations'] += 1
        else:
            counts['invalid_common_results'] += 1
        if example['metacats_operands'] is not None:
            operands = example['metacats_operands']; value = example['metacats_result']['value']
            assert extract_metacats_associations(**operands) == example['metacats_result'], example['name']
            if value is not None:
                assert mc.validate_metacats_association_set(value, **{k: operands[k] for k in ('analysis', 'documents', 'associations')}) == value
                counts['metacats_validations'] += 1
            else:
                counts['invalid_metacats_results'] += 1
        for calc in example['calculations']:
            function = {'biological_group_counts': biological_group_counts, 'msa_native_entropy': msa_native_entropy,
                'msa_reference_differences': msa_reference_differences}[calc['function']]
            assert function(calc['alignment'], **calc['arguments']) == calc['result'], example['name']
            counts['calculations'] += 1
        inline = example['downstream_operands'].get('inline_extraction')
        if inline:
            assert extract_inline_fasta_members(inline['binding'], **inline['arguments']) == inline['result']
            counts['inline_replays'] += 1
        counts['serialized_examples'] += 1
print(json.dumps({'status': 'passed', **counts, 'io_network_subprocess_forbidden_during_replay': True, 'native_jobs_run': 0}, indent=2))
