"""Reusable engineered single-treatment/matched-control MACS2 inputs."""
import hashlib


CHROMOSOME = 'chrSynthetic'
GENOME_SIZE = 12010000
READ_LENGTH = 50
TAG_COUNT = 12010


def engineered_bed6():
    """Return deterministic reads, without running a native scientific tool.

    The treatment has 1201 islands separated by 10kb, each with five distinct
    plus cuts and five distinct minus cuts separated by approximately 200bp.
    The matched control has the same total tags uniformly spaced every 1kb.
    Every row is a distinct 5-prime-cut/strand pair and lies inside the declared
    chromosome. Actual model fitting and peaks remain native measurements.
    """
    treatment, control = [], []
    for island in range(1201):
        center = 5000 + 10000 * island
        for j in range(5):
            cut = center - 100 + j
            treatment.append((cut, cut + READ_LENGTH, f't{island}p{j}', '+'))
            cut = center + 100 + j
            treatment.append((cut - READ_LENGTH, cut, f't{island}m{j}', '-'))
    for ordinal in range(TAG_COUNT):
        cut = 500 + 1000 * ordinal
        if ordinal % 2 == 0:
            control.append((cut, cut + READ_LENGTH, f'c{ordinal}', '+'))
        else:
            control.append((cut - READ_LENGTH, cut, f'c{ordinal}', '-'))
    def encode(rows):
        rows.sort(key=lambda row: (row[0], row[1], row[3], row[2]))
        return ''.join(f'{CHROMOSOME}\t{start}\t{end}\t{name}\t0\t{strand}\n'
            for start, end, name, strand in rows).encode('ascii')
    return encode(treatment), encode(control)


def file_identity(raw, fmt='bed6'):
    digest = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref='artifact_' + digest, sha256=digest,
        size_bytes=len(raw), format=fmt)


def engineered_reference():
    return dict(reference_id='engineered_chrSynthetic_12010000',
        assembly_accession_version=None, source_refs=[], aliases=[],
        contigs=[dict(chromosome=CHROMOSOME, length_bp=GENOME_SIZE,
            sequence_accession_version=None, sequence_sha256=None, source_refs=[])])

