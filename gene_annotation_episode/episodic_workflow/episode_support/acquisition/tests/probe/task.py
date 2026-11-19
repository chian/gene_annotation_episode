"""The task: one plan step per unit, each a call of a tool that runs acquisition library functions through the
Episode's custody-scoped store, as an episode's tool does."""
import importlib

from episode_runtime import ToolCall

PACKAGE = 'gene_annotation_episode.episodic_workflow.episode_support.acquisition.'
DATA = b'a file the external program wrote\n' * 40


def idle(arguments, ctx):
    return {'idle': True}


def attempt(call):
    try:
        return {'ok': call()}
    except Exception as error:
        return {'raised': type(error).__name__ + ': ' + str(error)}


def hmmer_capture(arguments, ctx):
    """Capture a file of the producer's directory as an artifact and read it back through custody."""
    module = importlib.import_module(PACKAGE + 'profile_model_preparation.' + arguments['axis']
                                     + '.native_hmmer_preparation_acquisition')
    store = ctx.store
    with store.scratch('profile') as scratch:
        (scratch.path / 'out').mkdir()
        (scratch.path / 'out' / 'profile.hmm').write_bytes(DATA)
        reference = module._capture_file(store, scratch.path, 'out/profile.hmm', 'text/plain')
    metadata = module._retained(store, reference)
    return {'reference': reference, 'size': metadata['size'], 'media_type': metadata['media_type'],
            'bytes_equal': store.get_artifact(reference) == DATA,
            'unheld': attempt(lambda: module._retained(store, arguments['unheld']))}


def blast_capture(arguments, ctx):
    """Capture the files of a native BLAST bundle directory: a file whose digest is the declared one, one whose
    digest is not, and one that is not in the directory."""
    module = importlib.import_module(PACKAGE + 'similarity_search.' + arguments['axis']
                                     + '.native_blast_acquisition')
    store, result = ctx.store, {'artifacts': [], 'invalid_artifacts': [], 'failures': []}
    from hashlib import sha256
    sha = sha256(DATA).hexdigest()
    with store.scratch('bundle') as scratch:
        (scratch.path / 'tabular.tsv').write_bytes(DATA)
        for relative, declared in (('tabular.tsv', sha), ('tabular.tsv', '0' * 64), ('missing.tsv', sha)):
            row = {'role': 'output', 'format': 'tabular', 'relative_path': relative}
            module._capture_file(store, result, scratch.path, row, sha=declared, size=len(DATA))
    kept = result['artifacts'][0]['artifact_ref']
    return {'result': result, 'retained': module._retained(store, kept), 'bytes_equal': store.get_artifact(kept) == DATA,
            'size': module._retained_size(store, kept)}


def protein_structure_capture(arguments, ctx):
    """Capture a file of a protein structure run as an artifact, verify it by its identity, and see a wrong
    length refused."""
    module = importlib.import_module(PACKAGE + 'protein_structure.native_protein_structure_acquisition')
    store = ctx.store
    with store.scratch('structure') as scratch:
        (scratch.path / 'table.tsv').write_bytes(DATA)
        identity = module._capture_file(store, str(scratch.path), 'table.tsv', 'text')
    return {'identity': identity, 'verified': module.verify_retained_protein_structure_file(store, identity),
            'wrong_length': attempt(lambda: module.verify_retained_protein_structure_file(
                store, {**identity, 'byte_length': identity['byte_length'] + 1})),
            'bytes_equal': store.get_artifact(identity['artifact_ref']) == DATA}


def protein_query(arguments, ctx):
    """The protein query of the homology search: a held reference is a query; a subject outside the scope is not."""
    module = importlib.import_module(PACKAGE + 'similarity_search.homology_query')
    store = ctx.store
    scope = {'subject_refs': [arguments['target']]}
    return {'target': attempt(lambda: module.protein_query(store, scope, arguments['target'], error_code='bad')['id']),
            'unknown': attempt(lambda: module.protein_query(store, scope, arguments['unheld'], error_code='bad'))}


TOOLS = {'idle': idle, 'hmmer_capture': hmmer_capture, 'blast_capture': blast_capture,
         'protein_structure_capture': protein_structure_capture, 'protein_query': protein_query}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    item = summary['plan'][step]
    return ToolCall(item['tool'], item['arguments'])


def action(response, summary, records, ctx):
    raise ValueError('acquisition_probe_asks_no_model')
