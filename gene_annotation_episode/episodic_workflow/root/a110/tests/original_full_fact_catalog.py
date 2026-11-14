"""Original Git catalog oracle on actual constructed state, without a constructor claim.

Schema helpers are shared, source-pinned own-axis dependencies. This independently
executes the original catalog/control bodies, not an independent schema engine.
"""
import ast
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a110'
LIB = PREFIX + '.library.received_execution_information'
SOURCE_SHA = '01ee297ce8c3ac079fb5b7618ef7ee1bfec72f3dcf5fa17230d95858a4602078'
PROOF_SHA = '388ec98532e30c468b6e4977e0e1f650dffcd3bcac4ba7dcaeea035dae2136a1'
METHODS = ('received_report_sources', 'fact_sources', '_forwards_bvbrc_reports', '_forwards_minhash_reports',
    '_has_appservice', '_has_rfam', '_has_uniprot', '_has_enrichr', '_has_addgene',
    '_appservice_sources', '_blast_reference_source', '_infernal_reference_source')
GLOBALS = ('TEXT', 'NATIVE_RESULT_ORIGIN', 'BLAST_GRADED_RETURN_SOURCE', 'BLAST_GRADED_RETURN_SCHEMA')
MAPPED = {'hmmer_native_result_views': 'historical_hmmer_native_result_views',
    'sequence_masking_result_views': 'historical_sequence_masking_result_views',
    'blast_utility_result_views': 'historical_blast_utility_result_views',
    'native_hmmer_acquisition': 'historical_native_hmmer_acquisition',
    'bvbrc_data_views': 'historical_bvbrc_data_views',
    'blast_result_views': 'historical_blast_result_fact_schema'}
DEPENDENCIES = ('execution_contracts.py', 'local_file_capture_results.py',
    'flux_balance_return_views.py', 'flux_balance_contracts.py', 'flux_balance_result_contracts.py', 'flux_balance_model_tools.py',
    'fluorescence_return_views.py', 'fluorescence_result_contracts.py',
    'protein_structure_result_views.py', 'protein_structure_contracts.py', 'native_fluorescence_results.py', 'native_flux_balance_results.py',
    'library/received_execution_information/historical_hmmer_native_result_views.py',
    'library/received_execution_information/historical_hmmer_graders.py',
    'library/received_execution_information/historical_sequence_masking_result_views.py',
    'library/received_execution_information/historical_blast_utility_result_views.py',
    'library/received_execution_information/historical_blast_utility_contracts.py',
    'library/received_execution_information/historical_blast_preparation_contracts.py',
    'library/received_execution_information/historical_blast_vdb_utility_contracts.py',
    'library/received_execution_information/historical_native_blast_standard_database_contracts.py',
    'library/received_execution_information/historical_native_blast_database_contracts.py',
    'library/received_execution_information/historical_fluorescence_contracts.py',
    'library/received_execution_information/historical_bvbrc_data_views.py',
    'library/received_execution_information/historical_bvbrc_data_schema.py',
    'library/received_execution_information/historical_blast_result_fact_schema.py',
    'library/received_execution_information/historical_native_hmmer_acquisition.py')

def digest(raw): return hashlib.sha256(raw).hexdigest()

def original_catalog(owner, role):
    assert role == 'scientific_process'
    # This exact case has a real ordinary backend and no optional API/native
    # declarations; do not substitute fake readers to exercise dormant branches.
    assert owner.api_execution is None
    assert not any(key.startswith('native_') for config in owner.resources.values() for key in config)
    assert owner.native_flux_balance_returns.ordinary_backend is owner.tool_registry.ordinary_flux_balance_backend
    for name in ('native_expression_nmf_results', 'atac_results', 'native_chromatin_interaction_results',
            'native_genomic_overlap_results', 'rna_structure_comparison_results', 'native_rna_structure_results',
            'native_blast_standard_database_results', 'native_blast_database_results',
            'native_hmmer_preparation_results', 'native_infernal_preparation_results', 'native_blast_results', 'native_infernal_results'):
        assert getattr(owner, name) is None
    fixture = Path(__file__).parent / 'fixtures/historical_fact_catalog'
    raw = (fixture / 'execution_episodes.py.source').read_bytes(); assert digest(raw) == SOURCE_SHA
    proof_raw = (fixture / 'source-proof.json').read_bytes(); assert digest(proof_raw) == PROOF_SHA
    proof = json.loads(proof_raw)
    assert proof['version'] == 'a110_default_fact_catalog_source_audit_v1'
    assert proof['whole_module_byte_and_ast_reversal'] is True
    root = Path(__file__).resolve().parents[5]
    axis = 'gene_annotation_episode/episodic_workflow/root/a110/'
    for relative in DEPENDENCIES:
        name = axis + relative; record = proof['source_after'][name]
        path = root / name
        assert not any(p.is_symlink() for p in (path, *path.parents))
        assert digest(path.read_bytes()) == record['sha256']
    tree = ast.parse(raw)
    original, = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ExecutionEpisodes']
    methods = {n.name: n for n in original.body if isinstance(n, ast.FunctionDef)}
    selected = [deepcopy(methods[name]) for name in METHODS]
    class Rebind(ast.NodeTransformer):
        def visit_ImportFrom(self, node):
            assert node.level == 1 and node.module is not None
            if node.module == 'bvbrc_data_views': assert [(a.name, a.asname) for a in node.names] == [('bvbrc_data_fact_sources', None)]
            if node.module == 'blast_result_views': assert [(a.name, a.asname) for a in node.names] == [('BLAST_HSP_FACT_SCHEMA', None)]
            node.module = (LIB + '.' + MAPPED[node.module]) if node.module in MAPPED else PREFIX + '.' + node.module
            node.level = 0
            return node
    for node in selected: Rebind().visit(node)
    assignments = [deepcopy(n) for n in tree.body if isinstance(n, ast.Assign)
        and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id in GLOBALS]
    assert {n.targets[0].id for n in assignments} == set(GLOBALS)
    namespace = {'deepcopy': deepcopy,
        'obj': importlib.import_module(PREFIX + '.execution_contracts').obj,
        'TerminalExecutionEpisodes': importlib.import_module(LIB + '.historical_practical_receipt_reader').HistoricalPracticalReceiptReader}
    oracle_class = ast.ClassDef(name='OriginalCatalog', bases=[], keywords=[], body=selected, decorator_list=[])
    program = ast.Module(body=assignments + [oracle_class], type_ignores=[])
    exec(compile(ast.fix_missing_locations(program), str(fixture / 'execution_episodes.py.source'), 'exec'), namespace)
    oracle = namespace['OriginalCatalog']()
    assert not set(METHODS) & set(vars(owner))
    # Deliberately shallow: same actual Store, backend, services and reader ports.
    # Every catalog/helper method comes from compiled original Git bodies.
    oracle.__dict__.update(vars(owner))
    expected = oracle.received_report_sources(role)
    assert expected['execution_file_source_refs']['meaning'] == 'Source references for selected local file streams actually retained by this results episode; no producing-execution or atomic-version identity is established.'
    assert expected['execution_file_capture_outcomes']['meaning'] == 'Recorded selected-file availability, original job status and file-custody qualifications; successful byte retention alone does not establish execution success or closed writers.'
    return expected
