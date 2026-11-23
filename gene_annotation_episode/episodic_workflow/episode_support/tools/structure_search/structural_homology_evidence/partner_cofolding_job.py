"""The job of A102's ``partner_cofolding`` (design note ``docs/plan/designs/a102_partner_cofolding.md``): the text of ``run_chai.py``,
the standalone program the batch job runs on Polaris (standard library and the ``chai_lab`` package of the chai environment), and the
batch job that runs it (``pbs_batch_job``).

THE PROGRAM. In its working directory it reads ``target.fasta`` (the target's protein sequence, as FASTA) and ``ligands.json``
(``{component id: SMILES}``). Per ligand it writes ``<id>/input.fasta`` with the records ``>protein|name=target`` and
``>ligand|name=<id>`` (the SMILES line) and runs ``chai_lab.chai1.run_inference`` there (ESM embeddings, no MSA server and no template
server since compute nodes are offline, seed 42), one ligand per GPU: the program starts one process per ligand, process ``k`` with
``CUDA_VISIBLE_DEVICES=k`` (so its one visible device is ``cuda:0``). It waits for them all, a process that fails fails the job, and
writes ``scores.json``: ``{component id: [per sample {aggregate_score, ptm, iptm, per_chain_pair_iptm, has_inter_chain_clashes,
chain_chain_clashes}]}``, each read by ``numpy`` from ``<id>/out/scores.model_idx_<k>.npz`` in sample order."""

from gene_annotation_episode.episodic_workflow.episode_support.jobs.pbs_batch_job import pbs_batch_job

PROGRAM_NAME = 'run_chai.py'
INPUT_FILES = ('target.fasta', 'ligands.json')
OUTPUT_FILE = 'scores.json'
SEED = 42
SCORE_FIELDS = ('aggregate_score', 'ptm', 'iptm', 'per_chain_pair_iptm', 'has_inter_chain_clashes', 'chain_chain_clashes')

RUN_CHAI_PY = '''"""Co-folds the target with each ligand, one ligand per GPU (one process per GPU). Reads target.fasta and ligands.json,
writes scores.json."""
import json
import os
import subprocess
import sys

SEED = 42
FIELDS = ('aggregate_score', 'ptm', 'iptm', 'per_chain_pair_iptm', 'has_inter_chain_clashes', 'chain_chain_clashes')


def target_sequence():
    with open('target.fasta') as handle:
        return ''.join(line.strip() for line in handle if not line.startswith('>'))


def fold_one(component_id, smiles, sequence):
    from pathlib import Path
    from chai_lab.chai1 import run_inference
    folder = Path(component_id)
    folder.mkdir()
    fasta = folder / 'input.fasta'
    fasta.write_text('>protein|name=target\\n' + sequence + '\\n>ligand|name=' + component_id + '\\n' + smiles + '\\n')
    run_inference(fasta_file=fasta, output_dir=folder / 'out', use_esm_embeddings=True, use_msa_server=False,
                  use_templates_server=False, seed=SEED, device='cuda:0')


def read_scores(component_id):
    import numpy
    samples, index = [], 0
    while os.path.exists(os.path.join(component_id, 'out', 'scores.model_idx_' + str(index) + '.npz')):
        arrays = numpy.load(os.path.join(component_id, 'out', 'scores.model_idx_' + str(index) + '.npz'))
        samples.append({field: arrays[field][0].tolist() for field in FIELDS})   # arrays carry a leading batch axis of 1
        index += 1
    return samples


def main():
    if len(sys.argv) == 3:
        with open('ligands.json') as handle:
            fold_one(sys.argv[1], json.load(handle)[sys.argv[1]], target_sequence())
        return
    with open('ligands.json') as handle:
        ligands = json.load(handle)
    processes = {}
    for gpu, component_id in enumerate(ligands):
        processes[component_id] = subprocess.Popen(
            [sys.executable, sys.argv[0], component_id, str(gpu)], env={**os.environ, 'CUDA_VISIBLE_DEVICES': str(gpu)})
    failed = [component_id for component_id, process in processes.items() if process.wait() != 0]
    if failed:
        raise SystemExit('chai failed for ' + ','.join(failed))
    with open('scores.json', 'w') as handle:
        json.dump({component_id: read_scores(component_id) for component_id in ligands}, handle)


main()
'''


def cofolding_batch_job(python_executable, allocation, *, env):
    """The PBS batch job that runs ``run_chai.py`` with ``python_executable`` (the chai environment's interpreter) under
    ``allocation`` (``pbs_batch_job``'s five operands) with ``env`` (the environment exports of the job: the chai environment)."""
    return pbs_batch_job([python_executable, '-u', PROGRAM_NAME], allocation, env=env)


__all__ = ['INPUT_FILES', 'OUTPUT_FILE', 'PROGRAM_NAME', 'RUN_CHAI_PY', 'SCORE_FIELDS', 'SEED', 'cofolding_batch_job']
