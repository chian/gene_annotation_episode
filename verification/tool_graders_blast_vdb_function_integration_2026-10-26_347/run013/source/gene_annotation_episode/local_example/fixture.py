"""Explicitly synthetic, fixed native-read workload; not a biological benchmark."""
import hashlib
from pathlib import Path
import random

from .service import JobStore, canonical, token
from ..local_jobs import LocalJobPolicy
from ..read_mapping import file_digest


def prepare(directory, *, reads=60000, read_length=10000, reference_length=5000000,
            reads_per_block=1000, seed=81273, max_cpu=1, candidates=None):
    directory=Path(directory).resolve(); directory.mkdir(parents=True,exist_ok=True)
    if (directory/'state.sqlite').exists(): raise ValueError('example_workspace_already_exists')
    if min(reads,read_length,reference_length,reads_per_block,max_cpu)<1 or read_length>reference_length:
        raise ValueError('invalid_synthetic_workload_dimensions')
    supplied=directory/'supplied'; supplied.mkdir()
    rng=random.Random(seed)
    genome=''.join(rng.choices('ACGT',k=reference_length))
    ref=supplied/'reference.fasta'; ref.write_text('>synthetic_reference\n'+genome+'\n')
    query=supplied/'reads.fastq'; complement=str.maketrans('ACGT','TGCA')
    with query.open('w') as output:
        for i in range(reads):
            start=rng.randrange(reference_length-read_length+1)
            strand='-' if i%2 else '+'
            original=genome[start:start+read_length]
            sequence=original if strand=='+' else original.translate(complement)[::-1]
            if i%20==0:
                sequence=''.join(rng.choices('ACGT',k=read_length))
            else:
                letters=list(sequence)
                for pos in rng.sample(range(read_length),max(1,read_length*8//100)):
                    letters[pos]=rng.choice('ACGT'.replace(letters[pos],''))
                sequence=''.join(letters)
            output.write(f'@synthetic_read_{i:07}\n{sequence}\n+\n'+('I'*read_length)+'\n')
    project=Path(__file__).resolve().parents[2]
    executable=project/'resources/software/minimap2-2.31/source/minimap2-2.31/minimap2'
    files=[{'path':str(p),'sha256':file_digest(p),'staged_name':name}
           for p,name in ((ref,'reference.fasta'),(query,'reads.fastq'))]
    basis={'kind':'synthetic_bacterial_scale_read_mapping_v1','seed':seed,'reads':reads,
        'read_length':read_length,'reference_length':reference_length,'substitution_fraction':.08,
        'unrelated_read_fraction':.05,'input_files':files,'preset':'map-ont','reads_per_block':reads_per_block}
    cfg={**basis,'workload_ref':token('workload',basis),'workspace_ref':token('workspace',str(directory)),
        'minimap2_candidates':list(candidates or [str(executable)]),'job_limits':LocalJobPolicy.from_config().to_dict(),
        'max_cpu':max_cpu,'identification':'Synthetic computational fixture; not sampled biological material or an annotation benchmark.'}
    store=JobStore(directory)
    store.db.execute('INSERT INTO example_configuration VALUES(1,?)',(canonical(cfg),));store.db.commit();store.close()
    (directory/'workload.json').write_text(canonical(cfg)+'\n')
    return cfg
