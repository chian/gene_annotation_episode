"""The held world of the real runs of the launch_local episode: a real Store holding a 12-protein FASTA, the real
job services (the detached local route on a workspace under the run's directory), the episode's settings (the
resource's Python and the bundled BLAST+ programs with their digests) and the entry commission. Nothing is faked."""
import hashlib
import sys
from pathlib import Path

from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services

from ..episode import LaunchLocal

PATH = LaunchLocal.binding_path
RESOURCE_ID = 'local_prep'
# The bundled BLAST+ is not in the live tree: it is read, as an input, from the disk checkout.
BLAST_BIN = Path('/home/chia/repos/gene_annotation_episode/resources/software/ncbi-blast-2.17.0+/bin')
POLICY = {'memory_bytes': 1024 ** 3, 'scratch_bytes': 256 * 1024 ** 2}
HANDOFF_UNIT = 4.0
PROTEINS = (
    ('ubq01', 'MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG'),
    ('hewl02', 'KVFGRCELAAAMKRHGLDNYRGYSLGNWVCAAKFESNFNTQATNRNTDGSTDYGILQINSRWWCNDGRTPGSRNLCNIPCSALLSSDITASVNCAKKIVSDGNGMNAWVAWRNRCKGTDVQAWIRGCRL'),
    ('gfp03', 'MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK'),
    ('calm04', 'ADQLTEEQIAEFKEAFSLFDKDGDGTITTKELGTVMRSLGQNPTEAELQDMINEVDADGNGTIDFPEFLTMMARKMKDTDSEEEIREAFRVFDKDGNGYISAAELRHVMTNLGEKLTDEEVDEMIREADIDGDGQVNYEEFVQMMTAK'),
    ('trx05', 'SDKIIHLTDDSFDTDVLKADGAILVDFWAEWCGPCKMIAPILDEIADEYQGKLTVAKLNIDQNPGTAPKYGIRGIPTLLLFKNGEVAATKVGALSKGQLKEFLDANLA'),
    ('cytc06', 'GDVEKGKKIFVQKCAQCHTVEKGGKHKTGPNLHGLFGRKTGQAPGFTYTDANKNKGITWKEETLMEYLENPKKYIPGTKMIFAGIKKKTEREDLIAYLKKATNE'),
    ('mb07', 'VLSEGEWQLVLHVWAKVEADVAGHGQDILIRLFKSHPETLEKFDRFKHLKTEAEMKASEDLKKHGVTVLTALGAILKKKGHHEAELKPLAQSHATKHKIPIKYLEFISEAIIHVLHSRHPGDFGADAQGAMNKALELFRKDIAAKYKELGYQG'),
    ('bpti08', 'RPDFCLEPPYTGPCKARIIRYFYNAKAGLCQTFVYGGCRAKRNNFKSAEDCMRTCGGA'),
    ('barn09', 'AQVINTFDGVADYLQTYHKLPDNYITKSEAQALGWVASKGNLADVAPGKSIGGDIFSNREGKLPGKSGRTWREADINYTSGFRNSDRILYSSDWLIYKTTDHYQTFTKIR'),
    ('sh310', 'TFVALYDYESRTETDLSFKKGERLQIVNNTEGDWWLAHSLSTGQTGYIPSNYVAPSD'),
    ('gb111', 'MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE'),
    ('snase12', 'ATSTKKLHKEPATLIKAIDGDTVKLMYKGQPMTFRLLLVDTPETKHPKKGVEKYGPEASAFTKKMVENAKKIEVEFDKGQRTDKYGRGLAYIYADGKMVNEALVRQGLAKVAYVYKPNNTHEQHLRKSEAQAKKEKLNIWSEDNADSGQ'))


def fasta(proteins=PROTEINS):
    return ''.join('>' + name + ' protein\n' + sequence + '\n' for name, sequence in proteins).encode()


def software():
    """The programs of the resource: path, digest and engine version, as the resource's configuration states them."""
    found = {}
    for program in ('makeblastdb', 'blastdbcmd', 'dustmasker', 'segmasker'):
        path = BLAST_BIN / program
        found[program] = {'executable': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'engine_version': '2.17.0+'}
    return found


SETTINGS = {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.05},
            'resources': {RESOURCE_ID: {'python': sys.executable, 'software': software()}}}


def world(directory, data=None):
    configuration = {
        'local': {RESOURCE_ID: {'workspace': str(directory / 'jobs'), 'policy': POLICY, 'cpu_threads': 1}},
        'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(directory / 'no_launch_instructions'),
        'tool_knowledge_directory': str(directory / 'no_tool_knowledge')}
    store = Store(directory / 'store')
    return {'store': store, 'services': job_services(configuration), 'directory': directory,
            'input_ref': store.artifact(fasta() if data is None else data, 'text/plain')}


def entry(held, **changes):
    assignment = {'version': 'blast_preparation_launch_assignment_v1', 'kind': 'database_build',
                  'molecule': 'protein', 'input_refs': [held['input_ref']], 'parse_seqids': True,
                  'hash_index': False, 'db_version': 5, 'resource_id': RESOURCE_ID, 'handoff_unit': HANDOFF_UNIT}
    return {'assignment': {**assignment, **changes}, 'message': {},
            'selection': ['execution_handoff_refs', 'execution_completed', 'plan_refs']}


def collaborators(held, calls, settings=None):
    return {'store': held['store'], 'model_provider': ModelProvider(load_config(), held['directory'] / calls,
                                                                    held['directory']),
            'continuation': {PATH: SETTINGS if settings is None else settings}, 'services': held['services']}
