"""Read only the two explicitly selected retained BAM headers inside the boundary."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import struct

import pysam


attempt = Path(os.environ['ATAC_REFERENCE_ATTEMPT'])
request = json.loads((attempt / 'inspection_inputs.json').read_text())


def identity(path):
    raw = path.read_bytes()
    return dict(path=str(path), size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


observations = []
for selected in request:
    path = Path(selected['path'])
    before = identity(path)
    assert before == selected
    # Pysam can synthesize missing @SQ lines. For these observations also read
    # the actual text section and establish byte equality, without reconstruction.
    with gzip.open(path, 'rb') as stream:
        assert stream.read(4) == b'BAM\x01'
        length = struct.unpack('<i', stream.read(4))[0]
        assert length >= 0
        original_text = stream.read(length)
        assert len(original_text) == length
    with pysam.AlignmentFile(str(path), 'rb', check_sq=False) as bam:
        reader_text = bam.text.encode('utf-8')
        native_dictionary = [dict(chromosome=name, length_bp=size)
                             for name, size in zip(bam.references, bam.lengths, strict=True)]
    assert reader_text == original_text
    header_path = attempt / (path.stem + '.sam_header.txt')
    header_path.write_bytes(reader_text)
    after = identity(path)
    assert after == before
    observations.append(dict(input_before=before, input_after=after,
                             header=identity(header_path),
                             raw_bam_text_equals_reader_text=True,
                             reader='pysam.AlignmentFile.text',
                             pysam_version=pysam.__version__,
                             native_dictionary=native_dictionary))
(attempt / 'BAM_HEADER_OBSERVATIONS.json').write_text(
    json.dumps(dict(origin='retained synthetic engineering BAM inputs; actual header inspection',
                    observations=observations), indent=2, allow_nan=False) + '\n')
print(json.dumps(observations, allow_nan=False))
