"""Original homology file identities and single-query normalization."""
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
from Bio import SeqIO
from gene_annotation_episode.domain import canonical


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def ref(kind, value):
    return kind+'_'+hashlib.sha256(canonical(value).encode()).hexdigest()[:24]


def normalize_query_fasta(query_fasta):
    """One actual query sequence, shared by ordering and class construction."""
    record = SeqIO.read(io.StringIO(query_fasta), 'fasta')
    if not record.seq:
        raise ValueError('empty_homology_query')
    return '>query\n'+str(record.seq).upper()+'\n'


@dataclass(frozen=True)
class FileAsset:
    path: Path
    sha256: str

    def __post_init__(self):
        if len(self.sha256) != 64 or any(c not in '0123456789abcdef' for c in self.sha256):
            raise ValueError('file_asset_digest_required')
        object.__setattr__(self, 'path', Path(self.path).expanduser().resolve())

    def as_record(self):
        return {'path': str(self.path), 'sha256': self.sha256}


