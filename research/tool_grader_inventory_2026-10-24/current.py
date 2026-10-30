"""Read-only source/deployment inventory; write only sibling current.json/md.

This script evaluates declared schemas and pure library information builders.
It never constructs a Store, freezes a run, executes a scientific operation,
opens SSH, queries a service, or changes existing source or historical state.
"""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import gene_annotation_episode.tools as registry_module
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary, _tool_information
from gene_annotation_episode.tool_information import make_tool_info, resource_kind, workflow_execution_catalogs
from gene_annotation_episode.public_configuration import ncbi_contact


def location(path, symbol=None):
    p = ROOT / path
    if symbol and p.suffix == '.py':
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == symbol:
                return {'path': path, 'line': node.lineno, 'symbol': symbol}
    return {'path': path}


def locations(*items):
    return [location(*item) if isinstance(item, tuple) else location(item) for item in items]


def file_fact(path):
    p = Path(path)
    p = p if p.is_absolute() else ROOT / p
    exists = p.is_file()
    return {'path': str(p), 'file_present': exists,
            'bytes': p.stat().st_size if exists else None,
            'executable_bit': os.access(p, os.X_OK) if exists else None,
            'scope': 'filesystem metadata only; binary was not executed'}


tree = ast.parse((ROOT / 'gene_annotation_episode/tools.py').read_text())
catalog_node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'catalog')
definitions_node = next(n for n in catalog_node.body if isinstance(n, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == 'definitions' for t in n.targets))
definitions = eval(compile(ast.Expression(definitions_node.value), '<declared-tool-schemas>', 'eval'), vars(registry_module))
ordinary = {name: {'name': name, 'description': row[0], 'input_schema': row[1]}
            for name, row in definitions.items()}
ordinary_lines = {key.value: key.lineno for key in definitions_node.value.keys}
resource_catalogs = workflow_execution_catalogs()
information, contracts = _tool_information(list(ordinary.values()), None)
profiles = {(row['name'], row['resources']): row['contract'] for row in contracts}

conditional_assignment = next(n for n in ast.walk(catalog_node) if isinstance(n, ast.Assign)
    and any(isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
            and t.slice.value == 'execution.estimate' for t in n.targets))
conditional_contract = {'name': 'execution.estimate', **eval(compile(ast.Expression(
    conditional_assignment.value), '<conditional-tool-schema>', 'eval'),
    {**vars(registry_module), 'result': ordinary})}

GROUPS = []


def group(key, names, category, owner, implementation, parser, values, dependencies, deployment,
          *, grader='not_implemented', evidence=(), limits=()):
    value = {'id': key, 'operation_names': names.split(), 'category': category,
        'proper_owner': owner, 'implementation': locations(*implementation),
        'output_readers_or_calculators': locations(*parser), 'native_or_source_values': values,
        'required_dependencies_and_configuration': dependencies,
        'deployment_status': deployment,
        'grader_binding': {'status': grader,
            'automatic_production_binding': False,
            'note': ('Transport/preparation/read operations are not separate scientific algorithm graders.'
                if category in {'infrastructure', 'data_reader', 'evidence_preparation', 'literature_excluded'}
                else 'Native numerical outputs are not by themselves a populated tool-scoring sheet.')},
        'evidence': locations(*evidence), 'limits': list(limits)}
    GROUPS.append(value)
    return value


ORDINARY_OWNER = 'Scoped scientific episode with this actual registry contract; a commissioning-only root remains restricted.'
LOCAL_NATIVE = ['Biopython/other named dependency in the selected interpreter',
    'Caller-owned LocalJobPolicy; functioning user systemd/cgroup protected worker for isolated native jobs; not probed here']

group('sequence_composition', 'sequence.inspect reads.inspect', 'measurement', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_perform'), ('gene_annotation_episode/tools.py', '_inspect_reads')],
    [('gene_annotation_episode/sequence_ops.py', 'inspect_sequence')],
    ['length', 'symbol counts', 'compatible alphabets', 'GC fraction and denominator', 'literal stop positions'],
    ['Registered actual sequence or selected original read subjects', 'Python runtime'],
    'Implemented in-process deterministic measurement; source inspected, no new measurement run.',
    limits=['Alphabet compatibility is not biological classification.'])
group('sequence_translation', 'sequence.translate', 'evidence_preparation', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_derive')], [('gene_annotation_episode/sequence_ops.py', 'translate')],
    ['protein symbols', 'selected code/frame/strand', 'used/trailing bases', 'internal and terminal stops'],
    ['Biopython', 'Registered nucleotide operand and explicitly selected NCBI code'],
    'Biopython distribution present; deterministic derivation bound. No new translation run.', grader='not_a_separate_algorithm_score')
group('sequence_views', 'sequence.view translation.codes', 'evidence_preparation', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_derive'), ('gene_annotation_episode/tools.py', '_perform')],
    [('gene_annotation_episode/sequence_views.py', 'view_sequence'), ('gene_annotation_episode/sequence_ops.py', 'translation_codes')],
    ['selected sequence segments/orientation and coordinate map', 'installed NCBI table names/start/stop codons'],
    ['Biopython', 'Registered operand for sequence.view'], 'Implemented local derivation/metadata reader.', grader='not_a_separate_algorithm_score')
group('biopython_pairwise', 'sequence.align reads.align', 'scientific_algorithm', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_prepare_sequence_work_async'), ('gene_annotation_episode/tools.py', '_sequence_worker_async'),
     ('gene_annotation_episode/tools.py', '_align_one'), ('gene_annotation_episode/tools.py', '_publish_read_alignments')],
    [('gene_annotation_episode/sequence_ops.py', 'align_pair'), ('gene_annotation_episode/sequence_worker.py', 'main')],
    ['native alignment score', 'paired/identical positions', 'identity fraction', 'query/reference coverage',
     'coordinates and aligned strings', 'model and gap scores'], LOCAL_NATIVE,
    'Biopython 1.88 present locally; local/global DNA/RNA/protein contracts. Historical Aurora analogue is a manual Gentner/Biopython global test, not an HPC sequence.align binding.',
    evidence=['verification/aurora_bioinformatics_2026-10-22_001/README.md', 'verification/aurora_bioinformatics_2026-10-22_001/execution.json'],
    limits=['One selected alignment is retained; pairwise score is not database significance.', 'Protein uses BLOSUM62; nucleotide match 2/mismatch -1; gaps -10/-0.5.'])
group('prodigal', 'genes.predict', 'scientific_algorithm', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_prepare_sequence_work_async'), ('gene_annotation_episode/tools.py', '_derive')],
    [('gene_annotation_episode/sequence_ops.py', 'predict_genes'), ('gene_annotation_episode/sequence_worker.py', 'main')],
    ['candidate CDS intervals/strand', 'partial endpoints', 'protein sequence', 'native confidence and score'],
    [*LOCAL_NATIVE, 'Pyrodigal', 'Selected translation code and meta/single mode; meta requires a native model for that code'],
    'Pyrodigal 3.7.1 present; native isolated-worker adapter exists. No current execution claimed.',
    limits=['Native confidence is not calibrated annotation correctness.', 'Circular origin-spanning calls and programmed recoding not resolved.'])
group('minimap2', 'reads.map', 'scientific_algorithm', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_native_mapping_async'), ('gene_annotation_episode/tools.py', '_publish_mapping'),
     ('gene_annotation_episode/read_mapping.py', 'run_mapping')],
    [('gene_annotation_episode/read_mapping.py', 'parse_paf_line'), ('gene_annotation_episode/read_mapping.py', 'project_output')],
    ['all PAF placements', 'mapping quality/ranking', 'native tags', 'cg CIGAR and cs long operations',
     'per-read coordinates', 'native source row byte locations'],
    [*LOCAL_NATIVE, 'Explicit local_tools.minimap2_executable', 'Caller CPU/cache', 'Immutable selected reads and actual selected references'],
    'Pinned minimap2 2.31-r1302 binary present. Package defaults and resources/local-tools.toml do not select its executable; caller must provide it.',
    evidence=['resources/software/minimap2-2.31/INSTALL.json', 'tests/test_native_read_mapping.py', 'docs/NATIVE_READ_MAPPING.md'],
    limits=['Supported presets: map-ont, map-pb, map-hifi, lr:hq, map-iclr, sr.', 'Unpaired mapping; no consensus/variant caller or function assignment.'])
group('infernal_cmsearch', 'rna.cmsearch', 'scientific_algorithm', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_native_cmsearch_async'), ('gene_annotation_episode/tools.py', '_publish_cmsearch')],
    [('gene_annotation_episode/rna_evidence.py', 'run_cmsearch'), ('gene_annotation_episode/rna_evidence.py', 'model_header'),
     ('gene_annotation_episode/rna_evidence.py', 'iter_fmt3')],
    ['bitscore/evalue/bias/GC', 'native inclusion/reporting', 'model and target lengths/coordinates',
     'strand/truncation/pass', 'complete retained stdout/table/stderr'],
    [*LOCAL_NATIVE, 'Explicit cmsearch executable (supplied in resources/local-tools.toml, absent from package defaults)',
     'One acquired ASCII covariance model and actual nucleotide operand'],
    'Infernal 1.1.5 installed binary/build receipt present. Old Rfam calibration fixture paths named by docs/tests are absent in this checkout.',
    evidence=['resources/software/infernal-1.1.5-build.json', 'resources/local-tools.toml', 'docs/RNA_EVIDENCE.md', 'tests/test_rna_evidence.py'],
    limits=['Native query is model, target is sequence; model consensus coordinates are not physical reference residues.',
            'Infernal 1.1.5 mixed reporting/inclusion-mode limitation is retained.'])
group('alignment_site_readers', 'sequence.sites result.blast.hsp', 'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_alignment_sites'), ('gene_annotation_episode/tools.py', '_perform')],
    [('gene_annotation_episode/sequence_ops.py', 'compare_sites'), ('gene_annotation_episode/read_mapping.py', 'compare_paf_sites'),
     ('gene_annotation_episode/blast_result_views.py', 'read_blast_hsp')],
    ['selected residue relationships', 'gap/insertion/outside-alignment state', 'quality characters and declared encoding',
     'bounded exact BLAST HSP alignment columns and native metadata'],
    ['Existing native alignment/source records', 'BLAST HSP reader requires explicitly permitted observation receipt and scope'],
    'Implemented local result readers. No new algorithm execution.', grader='reader_only',
    evidence=['tests/test_blast_result_views.py', 'tests/test_blast_typed_return_integration.py'])
group('genbank_neighborhood', 'reference.neighborhood', 'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_perform')], [('gene_annotation_episode/comparative_ops.py', 'genbank_neighborhood'),
    ('gene_annotation_episode/acquisition.py', 'parse_genbank')],
    ['selected source feature/strand/order/window', 'record versus original coordinate mapping', 'partial/unavailable context'],
    ['Biopython', 'Acquired GenBank reference with original bytes', 'Explicit locus/protein/coordinate selector and left/right bounds'],
    'Implemented local comparative data reader; does not infer orthology or operon function.', grader='reader_only')
group('rfam_batch', 'public.rfam.search public.rfam.collect', 'scientific_algorithm', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_acquire_async'), ('gene_annotation_episode/provider_jobs.py', 'search'),
     ('gene_annotation_episode/provider_jobs.py', 'collect'), ('gene_annotation_episode/tools.py', '_import_rfam_discovery')],
    [('gene_annotation_episode/acquisition.py', 'rfam_submit'), ('gene_annotation_episode/acquisition.py', 'rfam_result'),
     ('gene_annotation_episode/rfam_discovery.py', 'result_body'), ('gene_annotation_episode/rfam_discovery.py', 'hit_row')],
    ['reported RNA-family hits', 'score/evalue/GC', 'native strand and physical sequence interval', 'complete native alignment body'],
    ['Public batch.rfam.org service', 'Registered nucleotide operand', 'Original durable job identity for collection'],
    'Implemented API protocol. Historical 119-nt official-example success is documented; referenced validation/providers/rfam-batch-calibration files are absent here. No live availability probe.',
    evidence=['docs/RFAM_DISCOVERY.md', 'tests/test_rfam_discovery.py'],
    limits=['No exposed database/model release or native command/default thresholds.', 'collect is acquisition of the same search, not a new algorithm/grader.'])
group('rfam_model', 'public.rfam.model', 'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/acquisition.py', 'rfam_model'), ('gene_annotation_episode/tools.py', '_import_rfam')],
    [('gene_annotation_episode/rna_evidence.py', 'model_header')],
    ['ASCII covariance model', 'family metadata and source header/cutoffs', 'model consensus length'],
    ['Rfam family CM/JSON HTTP endpoints', 'Explicit RF accession'],
    'Implemented model and optional metadata acquisition; historical fixtures missing at their referenced path.', grader='reader_only',
    evidence=['docs/RNA_EVIDENCE.md'])
group('blast', 'public.blast.search public.blast.collect api.blast.prepare api.blast.submit api.blast.status api.blast.fetch',
    'scientific_algorithm', 'public.* is an ordinary scoped operation; api.* belongs to launch_api/results under its original assigned service request.',
    [('gene_annotation_episode/tools.py', '_acquire_async'), ('gene_annotation_episode/tools.py', '_import_blast'),
     ('gene_annotation_episode/api_blast.py', 'NCBIBlastService'), ('gene_annotation_episode/api_services.py', 'build_service'),
     ('gene_annotation_episode/api_service_execution.py', 'APIServiceExecution')],
    [('gene_annotation_episode/blast_search.py', 'document'), ('gene_annotation_episode/blast_search.py', 'hsp_row'),
     ('gene_annotation_episode/blast_grading_inputs.py', 'parse_blast_json'), ('gene_annotation_episode/blast_grading_inputs.py', 'parse_blast_tabular')],
    ['all native subject/HSP scores and statistics', 'coordinates/frames/alignment strings', 'retained source bytes',
     'standalone pairwise/database numerical scoring sheets'],
    ['Installed ncbi-blast-skill/scripts/ncbi_blast.py', 'Configured contact for submission and provider access directory for pacing',
     'Original RID for status/fetch', 'API resource registration for api.*'],
    'API execution implemented for blastn, blastp, blastx, tblastn, tblastx. Current contact present (value omitted). BLAST+ 2.17.0 binary present with real local two-sequence test. Live API grading checkpoint remains WAITING/blocked. No HPC BLAST deployment proven.',
    grader='standalone_pairwise_and_database_sheets_not_bound_to_production',
    evidence=['docs/BLAST_TOOL_GRADERS.md', 'verification/w04_blast_graders_2026-10-24_001/VERIFICATION.md',
              'verification/w04_blast_graders_2026-10-24_001/native_pair/execution.json'],
    limits=['Ordinary execution parser accepts one database query; grader parser separately supports one-pair bl2seq.',
            'Resource provenance does not select the parser. HPC format fixture success does not establish HPC execution.',
            'Native JSON2/JSON15 and declared tabular readers have explicit missing-data semantics.'])
group('uniprot', 'public.uniprot.record public.uniprot.search api.uniprot.record api.uniprot.search api.uniprot.collect',
    'data_reader', 'public.* ordinary scoped registry; api.* assigned launch_api/results.',
    [('gene_annotation_episode/acquisition.py', 'uniprot_record'), ('gene_annotation_episode/acquisition.py', 'uniprot_search'),
     ('gene_annotation_episode/api_uniprot.py', 'UniProtService'), ('gene_annotation_episode/tools.py', '_import')],
    [('gene_annotation_episode/acquisition.py', 'parse_uniprot'), ('gene_annotation_episode/acquisition.py', 'uniprot_pagination'),
     ('gene_annotation_episode/blast_reference_metadata.py', 'read_uniprot_metadata')],
    ['protein sequences/accessions/source labels', 'EC/source features/comments/references', 'cursor/release metadata',
     'separate BLAST metadata reader retains explicit EC evidence and full-sequence identity'],
    ['Installed uniprot-skill/scripts/rest_request.py', 'requests', 'UniProt REST service', 'API registration for api.*'],
    'Client script present. Recorded 2026-10-23 live API launch/monitor/results path completed for P0AAW1; not re-probed.',
    grader='reader_only; BLAST-specific metadata reader callable separately',
    evidence=['docs/API_SERVICE_EXPANSION_VERIFICATION_2026-10-23_001.md', 'verification/api_service_expansion_2026-10-23_001/live_public_002/report.json'])
group('ncbi_data', 'public.ncbi.search public.ncbi.sequence public.taxonomy', 'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/acquisition.py', 'ncbi_search'), ('gene_annotation_episode/acquisition.py', 'ncbi_sequence'),
     ('gene_annotation_episode/acquisition.py', 'taxonomy'), ('gene_annotation_episode/tools.py', '_import')],
    [('gene_annotation_episode/acquisition.py', 'parse_genbank'), ('gene_annotation_episode/blast_reference_metadata.py', 'read_ncbi_taxonomy'),
     ('gene_annotation_episode/blast_reference_metadata.py', 'read_ncbi_assembly_metadata')],
    ['Entrez search JSON', 'GenBank/GenPept sequence and source features', 'taxonomy XML',
     'standalone taxonomy/explicitly linked assembly metadata for BLAST sheets'],
    ['NCBI E-utilities HTTP endpoints', 'Biopython for GenBank', 'Actual reference/assembly link for the standalone assembly reader'],
    'Implemented ordinary HTTP acquisition. Taxonomy is retained as XML; generic _import does not create typed lineage. BLAST taxonomy reader is separate. No ordinary assembly-report fetch binding.',
    grader='reader_only; BLAST-specific taxonomy and assembly readers separate',
    limits=['NCBI search permits protein, nuccore, assembly, taxonomy, biosample, bioproject, pubmed; PubMed usage is literature scope and excluded from this grader work.'])
group('rhea', 'public.rhea.search public.rhea.reaction', 'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/acquisition.py', 'rhea_search'), ('gene_annotation_episode/acquisition.py', 'rhea_reaction'),
     ('gene_annotation_episode/tools.py', '_import_chemistry')],
    [('gene_annotation_episode/chemistry.py', 'rhea_response'), ('gene_annotation_episode/chemistry.py', 'rhea_row'),
     ('gene_annotation_episode/chemistry.py', 'rhea_equation')],
    ['source equation/direction', 'native balance/transport flags', 'explicit participants/coefficients/locations'],
    ['Installed rhea-skill/scripts/rest_request.py', 'Rhea public JSON service'],
    'Client script and source-preserving parser present; no current service request. This is source chemistry, not a target reaction calculator.', grader='reader_only',
    evidence=['docs/REACTION_AND_CHEMICAL_EVIDENCE.md'])
group('chebi', 'public.chebi.search public.chebi.compound', 'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/acquisition.py', 'chebi_search'), ('gene_annotation_episode/acquisition.py', 'chebi_compound'),
     ('gene_annotation_episode/tools.py', '_import_chemistry')],
    [('gene_annotation_episode/chemistry.py', 'chebi_response'), ('gene_annotation_episode/chemistry.py', 'chemical_row')],
    ['source chemical identity/structure strings', 'formula/charge/mass fields where supplied', 'ontology/source relations and pagination'],
    ['Installed chebi-skill/scripts/rest_request.py', 'ChEBI public service'],
    'Client script and parser present; no current service request.', grader='reader_only', evidence=['docs/REACTION_AND_CHEMICAL_EVIDENCE.md'])
group('bvbrc_data', 'api.bvbrc.query api.bvbrc.result', 'data_reader', 'Assigned launch_api/results; public Data API only.',
    [('gene_annotation_episode/api_bvbrc.py', 'BVBRCDataService'), ('gene_annotation_episode/api_bvbrc.py', 'BVBRCDataClient')],
    [('gene_annotation_episode/api_bvbrc.py', '_parse'), ('gene_annotation_episode/api_bvbrc.py', 'publish')],
    ['native genome/genome_feature/protein_family_ref rows', 'Content-Range and exact fields/filter/sort/page'],
    ['Configured bvbrc_data API resource', 'Public Data API service; no computational job/auth binding supplied here'],
    'Implemented for three collections. Recorded live 2026-10-23 feature page and connected original-response reuse succeeded. Computational AppService/Workspace execution absent.',
    grader='reader_only', evidence=['docs/API_SERVICE_EXPANSION_VERIFICATION_2026-10-23_001.md'],
    limits=['Full upstream BV-BRC tool inventory is assigned to a separate worker.'])
group('hmmer_api', 'api.hmmer.databases api.hmmer.prepare api.hmmer.submit api.hmmer.status api.hmmer.check_handoff api.hmmer.result',
    'scientific_algorithm', 'Assigned launch_api; api.hmmer.result in assigned results episode.',
    [('gene_annotation_episode/api_execution.py', 'HMMERAPIExecution'), ('gene_annotation_episode/api_service_execution.py', 'APIServiceExecution'),
     ('gene_annotation_episode/acquisition.py', 'hmmer_submit'), ('gene_annotation_episode/tools.py', 'publish_hmmer_result')],
    [('gene_annotation_episode/acquisition.py', 'parse_hmmer'), ('gene_annotation_episode/tools.py', '_publish_hmmer_rows')],
    ['hit bitscores/evalues/inclusion/reporting', 'domain scores/conditional/independent evalues',
     'algorithm-specific sequence/model coordinate mapping', 'alignment coverage and native identity when supplied'],
    ['Explicit hmmer_api resource/service assignment', 'Original protein query/algorithm/database/parameters',
     'EBI HMMER public service and original UUID'],
    'Implemented phmmer and hmmscan API route. Current public.* HMMER search names removed. Historical service/fixture records do not establish present service availability.',
    evidence=['docs/EXECUTION_WIRING.md', 'gene_annotation_episode/launch_instruction_library/api-service.md'],
    limits=['Database inventory is discovery, not a search.', 'Six operation names represent lifecycle of two algorithms, not six graders.', 'No API hmmsearch/jackhmmer/nhmmer binding.'])
group('phmmer_local', 'homology.environment homology.configure homology.stage homology.submit homology.resume_start homology.check_handoff homology.sample homology.extract homology.coverage homology.errors',
    'scientific_algorithm', 'Legacy job_launch/job_monitor/job_results, or existing local HomologyResourceAdapter launch_local/results; no direct ordinary registry grant.',
    [('gene_annotation_episode/homology_episodes.py', 'HomologyEpisodes'), ('gene_annotation_episode/homology_jobs.py', 'HomologyJobs'),
     ('gene_annotation_episode/resource_episodes.py', 'LocalHomologyResource')],
    [('gene_annotation_episode/homology_results.py', 'HomologyResults'), ('gene_annotation_episode/phmmer_result_worker.py', 'extract'),
     ('gene_annotation_episode/phmmer_format.py', 'hit_rows'), ('gene_annotation_episode/phmmer_format.py', 'alignment_rows'),
     ('gene_annotation_episode/phmmer_format.py', 'paired_segments')],
    ['sequence/domain bitscores/evalues', 'native gapped alignments', 'paired/identical residues and union geometry',
     'source/query/database identities', 'parse/native completeness and specific row failures'],
    [*LOCAL_NATIVE, 'Caller HomologyJobs registry with pinned executable/reference FASTA hashes, CPU and allowed native_defaults/maximum_sensitivity modes'],
    'HMMER 3.4 phmmer executable and pinned case reference FASTA present. Case config fixes 575,748 sequences/209,017,843 residues. Historical tiny/full-corpus local records exist; no new search or manager probe.',
    evidence=['cases/gene_001/execution.toml', 'docs/HOMOLOGY_EXECUTION.md', 'docs/HOMOLOGY_RESULTS.md'],
    limits=['Ten lifecycle/read names share one scientific phmmer result family.', 'NativePhmmerInput can parse supplied files with provenance; it does not supply an HPC transport.'])
group('material_intake', 'material.parse material.annotations material.from_source material.read material.members material.errors material.member material.header',
    'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_perform'), ('gene_annotation_episode/materials.py', 'parse_material')],
    [('gene_annotation_episode/material_parsing.py', 'records'), ('gene_annotation_episode/genbank_intake.py', 'records'),
     ('gene_annotation_episode/materials.py', 'annotation_page'), ('gene_annotation_episode/materials.py', 'read_member'),
     ('gene_annotation_episode/materials.py', 'read_header')],
    ['FASTA/FASTQ/raw/GenBank records', 'native qualities/titles', 'source feature annotations', 'parser errors and original byte windows'],
    ['Registered supplied source/material', 'Biopython', 'Original immutable artifact custody'],
    'Implemented format parsing/readers. text/opaque preserve bytes; no biological classification or scorer is supplied.', grader='reader_only')
group('read_library', 'library.members library.select library.read', 'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_perform'), ('gene_annotation_episode/library_targets.py', 'member_page'),
     ('gene_annotation_episode/library_targets.py', 'select')],
    [('gene_annotation_episode/materials_packing.py', 'component_window')],
    ['original-read inventory and stable member identity', 'explicit immutable selected subset', 'sequence/quality windows'],
    ['Registered immutable original read collection'], 'Implemented local reads/subset preparation; no biological scorer.', grader='reader_only')
group('record_and_source_read', 'state.query source.read', 'data_reader', ORDINARY_OWNER,
    [('gene_annotation_episode/tools.py', '_perform')], [('gene_annotation_episode/materials.py', 'source_window')],
    ['bounded stored records', 'exact original or normalized source byte windows'],
    ['Existing scoped records/source artifacts'], 'Implemented auxiliary reader usable across biological and literature evidence.', grader='reader_only')
group('public_job_inventory', 'public.search.jobs', 'infrastructure', ORDINARY_OWNER,
    [('gene_annotation_episode/provider_jobs.py', 'jobs'), ('gene_annotation_episode/tools.py', '_perform')], [],
    ['durable original remote job states/handles'], ['Existing RemoteSearches registry'],
    'Implemented ownership/status inventory; no scientific measurement.', grader='not_a_scientific_grader')
group('practical_execution', 'practical.inspect practical.inventory.refresh practical.context.set practical.directory.create practical.file.write practical.file.read practical.command.run practical.job.start practical.job.status practical.job.collect',
    'infrastructure', 'Assigned launch_local or launch_hpc under fixed job and caller resource configuration.',
    [('gene_annotation_episode/practical_resource_episodes.py', 'operation_catalog'), ('gene_annotation_episode/practical_resource_episodes.py', 'PracticalResourceEpisodes'),
     ('gene_annotation_episode/practical_execution_operations.py', 'LocalPracticalOperations'), ('gene_annotation_episode/practical_pbs_operations.py', 'PBSPracticalOperations')],
    [('gene_annotation_episode/practical_execution_records.py', 'assess_validations')],
    ['file existence/hash/context facts', 'native command exit/logs', 'original local/PBS attempt state', 'requested output predicates'],
    ['local: explicit workspace/policy and user-systemd protected lifecycle',
     'hpc: explicit pbs_ssh workspace, ssh_argv, remote python_executable, account; reachable authenticated route, PBS and algorithm/database preparation'],
    'Generic local/PBS primitives implemented; actual bioinformatics availability depends on the assigned command/environment. Only historical manual Aurora pairwise test verified here. No fresh SSH/PBS probe.',
    grader='not_a_scientific_grader', evidence=['docs/PRACTICAL_EXECUTION.md', 'verification/aurora_bioinformatics_2026-10-22_001/README.md'],
    limits=['20 variants are ten generic operations in local/HPC.', 'An arbitrary executable passed via argv is not automatically an installed or registered biological tool.',
            'Aurora project storage BioReason-Aurora-Test and new-job EpiCalib account retained.'])
group('execution_capability_and_bytes', 'execution.capabilities execution.results.status execution.results.collect execution.results.read',
    'infrastructure', 'execution.capabilities in launch; native result operations in original assigned results episode.',
    [('gene_annotation_episode/execution_episodes.py', 'launch_operation_catalog'), ('gene_annotation_episode/execution_episodes.py', 'native_result_operation_catalog'),
     ('gene_annotation_episode/execution_episodes.py', 'ExecutionEpisodes')], [],
    ['caller-bound capabilities/inventory', 'original native attempt status', 'bounded selected output-file bytes'],
    ['ExecutionServiceFactory caller resources', 'Original handoff/assignment and requested paths'],
    'Implemented generic acquisition for local/PBS; result bytes have no automatic algorithm parser/grader.', grader='not_a_scientific_grader',
    limits=['One local-tagged launch capability info row plus three local and three HPC result variants.'])
group('progress', 'progress.observe progress.read progress.log', 'infrastructure', 'Monitoring episode with explicit original target and requested fields.',
    [('gene_annotation_episode/episode_monitoring.py', 'MonitorEpisodes'), ('gene_annotation_episode/execution_progress.py', 'ExecutionProgressProvider')], [],
    ['observable original native/service state', 'recorded progress fields/log windows'],
    ['Bound progress provider and scoped original target handle'],
    'Three operations each advertised for API/local/HPC; not scientific algorithms.', grader='not_a_scientific_grader')
group('literature_and_document_exclusions', 'public.pmc.versions public.pmc.files public.pmc.asset public.literature.search public.literature.read source.archive.members source.archive.extract source.xlsx.sheets source.xlsx.rows source.pdf.info source.pdf.text source.pdf.page image.view',
    'literature_excluded', 'Existing scoped source/literature operations.',
    ['gene_annotation_episode/document_tools.py', 'gene_annotation_episode/spreadsheet_tools.py', 'gene_annotation_episode/literature_assets.py', 'gene_annotation_episode/image_evidence.py'],
    [], ['source/document representations only'], ['Retained original source and corresponding reader dependencies'],
    'Counted only to reconcile the complete catalog; literature grader inventory/implementation is outside this task.', grader='out_of_scope')

by_name = {}
for g in GROUPS:
    for name in g['operation_names']:
        if name in by_name:
            raise ValueError('duplicate inventory group: ' + name)
        by_name[name] = g
assert set(ordinary) <= set(by_name), set(ordinary) - set(by_name)
assert {row['name'] for rows in resource_catalogs.values() for row in rows} <= set(by_name)

entries = []
for row in information:
    name, resource = row['name'], row['resources']
    g = by_name[name]
    is_ordinary = name in ordinary and resource_kind(name) == resource
    entries.append({**row, 'input_schema': deepcopy(profiles[(name, resource)]['input_schema']),
        'catalog_surface': 'ordinary_registry' if is_ordinary else 'resource_execution_declaration',
        'inventory_group': g['id'], 'category': g['category'], 'proper_owner': g['proper_owner'],
        'scientific_grader_binding': g['grader_binding']['status'],
        'runtime_availability': 'Requires actual receiver binding, assigned operands and dependencies; declaration is not availability.',
        'definition': location('gene_annotation_episode/tools.py') | {'line': ordinary_lines[name]}
            if is_ordinary else location('gene_annotation_episode/tool_information.py', 'workflow_execution_catalogs')})

manuals = []
for folder in ('knowledge', 'launch_instruction_library'):
    path = ROOT/'gene_annotation_episode'/folder/'index.json'
    manifest = json.loads(path.read_text())
    for row in manifest['entries']:
        manuals.append({'library': folder, **row, 'manifest': str(path.relative_to(ROOT)),
            'all_named_operations_have_a_current_declaration': all(name in by_name for name in row['tool_names'])})

packages = {}
for name in ('biopython', 'pyrodigal', 'pyhmmer', 'numpy', 'scipy', 'requests', 'Pillow', 'jsonschema'):
    try: packages[name] = {'present': True, 'version': version(name)}
    except PackageNotFoundError: packages[name] = {'present': False, 'version': None}
binary_dirs = {}
for folder in ('resources/software/infernal-1.1.5-install/bin', 'resources/software/ncbi-blast-2.17.0+/bin',
               'resources/software/infernal-1.1.5/hmmer/src'):
    binary_dirs[folder] = [file_fact(p) for p in sorted((ROOT/folder).iterdir())
        if p.is_file() and os.access(p, os.X_OK) and p.suffix not in {'.sh', '.pl', '.py'}]
skill_root = Path('/home/chia/.codex/plugins/cache/openai-curated-remote/life-science-research/1.0.3/skills')
skill_clients = [file_fact(skill_root/skill/'scripts'/script) for skill, script in (
    ('uniprot-skill', 'rest_request.py'), ('ncbi-blast-skill', 'ncbi_blast.py'),
    ('rhea-skill', 'rest_request.py'), ('chebi-skill', 'rest_request.py'))]

# Pure in-memory diagnostic of the actual resolver's discovery/selection mismatch.
# It does not freeze data or construct/run an episode.
library = ScientificToolLibrary.__new__(ScientificToolLibrary)
library._check = lambda: None
library.supports_tool_info = True
library._information = {(row['name'], row['resources']): row for row in information}
library._resource_contracts = profiles
literal = library.retrieve_literal_test('BLAST')
choice = {'name': 'api.blast.submit', 'resources': 'api'}
try:
    library.resolve_tool_info([choice], list(ordinary.values()))
    failure = None
except ValueError as error:
    failure = str(error)
diagnostic = {'method': 'Pure in-memory declared metadata/resolver calls; no workflow or scientific operation executed.',
    'literal_request': 'BLAST', 'literal_selected_pairs': [{k: row[k] for k in ('name', 'resources')}
        for row in literal['child_tool_info']], 'selected_pair': choice,
    'selected_pair_was_discovered': choice in [{k: row[k] for k in choice} for row in literal['child_tool_info']],
    'receiver_catalog': 'ordinary ToolRegistry definitions, matching WorkflowServices.tool_catalog',
    'materialization_failure': failure,
    'interpretation': 'The mismatch concerns unfiltered literal discovery advertising a resource-role operation for the scientific primitive slot. Refusing direct scientific/root execution is correct ownership; do not fix by broadening root privileges.',
    'proper_path': 'Scientific parent commissions launch with a fixed service request; launch selects configured API resource; launch_api owns api.blast.*; results owns original-RID acquisition.',
    'missing_link': 'No automatic child_tool_info-to-launch assignment conversion is supplied; resource operations must remain linked to their proper child-owned contracts.',
    'sources': locations(('gene_annotation_episode/runtime.py', 'execute_tool'),
        ('gene_annotation_episode/episode_services.py', 'tool_catalog'), ('gene_annotation_episode/scientific_process_episodes.py', '_assignment'),
        ('gene_annotation_episode/scientific_process_episodes.py', '_tool_resolution_for'),
        ('gene_annotation_episode/scientific_tool_retrieval.py', 'retrieve'),
        ('gene_annotation_episode/scientific_tool_library.py', 'retrieve_literal_test'),
        ('gene_annotation_episode/scientific_tool_library.py', 'resolve_tool_info'))}
assert diagnostic['selected_pair_was_discovered'] and failure == 'scientific_tool_contract_changed:api.blast.submit:api'

native_families = [
    {'family': 'Biopython PairwiseAligner', 'group': 'biopython_pairwise', 'programs': ['local/global protein', 'local/global DNA/RNA'],
     'resources': [{'resource': 'local', 'status': 'actual registry binding'},
                   {'resource': 'hpc/Aurora', 'status': 'historical manual Gentner global protein test only; no sequence.align HPC entry'}]},
    {'family': 'Prodigal/Pyrodigal', 'group': 'prodigal', 'programs': ['meta', 'single'],
     'resources': [{'resource': 'local', 'status': 'actual registry binding'}]},
    {'family': 'minimap2', 'group': 'minimap2', 'programs': ['map-ont', 'map-pb', 'map-hifi', 'lr:hq', 'map-iclr', 'sr'],
     'resources': [{'resource': 'local', 'status': 'actual registry binding; explicit executable required'}]},
    {'family': 'Infernal cmsearch', 'group': 'infernal_cmsearch', 'programs': ['cmsearch'],
     'resources': [{'resource': 'local', 'status': 'actual registry binding; selected CM and explicit executable required'}]},
    {'family': 'HMMER phmmer', 'group': 'phmmer_local', 'programs': ['phmmer'],
     'resources': [{'resource': 'local', 'status': 'actual resource/job-role binding'},
                   {'resource': 'api', 'status': 'actual HMMER assigned API binding; same result family needs API format reader'}]},
    {'family': 'HMMER hmmscan', 'group': 'hmmer_api', 'programs': ['hmmscan'],
     'resources': [{'resource': 'api', 'status': 'actual HMMER assigned API binding'},
                   {'resource': 'local', 'status': 'binary present; no dedicated hmmscan callable or result importer'}]},
    {'family': 'Rfam batch Infernal cmscan', 'group': 'rfam_batch', 'programs': ['provider batch RNA-family scan'],
     'resources': [{'resource': 'api', 'status': 'actual ordinary API binding'},
                   {'resource': 'local', 'status': 'Infernal cmscan binary present; no dedicated local cmscan callable'}]},
    {'family': 'NCBI BLAST', 'group': 'blast', 'programs': ['blastn', 'blastp', 'blastx', 'tblastn', 'tblastx'],
     'resources': [{'resource': 'api', 'status': 'actual ordinary and assigned API bindings for five listed programs'},
                   {'resource': 'local', 'status': 'installed suite; real blastp two-sequence verification helper; no dedicated ToolRegistry local BLAST operation'},
                   {'resource': 'hpc', 'status': 'standalone JSON/tabular graders accept retained output; no deployed named BLAST HPC binding or completed HPC test'}]},
]

function_specs = [
    ('gene_annotation_episode/blast_graders.py', 'grade_blast_result', 'facade'),
    ('gene_annotation_episode/blast_grading_inputs.py', 'parse_blast_json', 'native_reader'),
    ('gene_annotation_episode/blast_grading_inputs.py', 'parse_blast_tabular', 'native_reader'),
    ('gene_annotation_episode/blast_pairwise_grader.py', 'alignment_components', 'component_calculator'),
    ('gene_annotation_episode/blast_pairwise_grader.py', 'build_pairwise_sheet', 'sheet_builder'),
    ('gene_annotation_episode/blast_database_grader.py', 'build_database_sheet', 'sheet_builder'),
    ('gene_annotation_episode/blast_database_grader.py', 'calculate_database_probabilities', 'replaceable_sheet_calculator'),
    ('gene_annotation_episode/blast_reference_metadata.py', 'read_uniprot_metadata', 'metadata_reader'),
    ('gene_annotation_episode/blast_reference_metadata.py', 'read_ncbi_taxonomy', 'metadata_reader'),
    ('gene_annotation_episode/blast_reference_metadata.py', 'read_ncbi_assembly_metadata', 'metadata_reader'),
    ('gene_annotation_episode/blast_reference_metadata.py', 'attach_taxonomy', 'exact_taxid_join'),
]
grader_functions = [{**location(path, name), 'kind': kind} for path, name, kind in function_specs]

aux_counts = Counter(row['category'] for row in entries)
ordinary_count = len(ordinary)
excluded = sum(row['catalog_surface'] == 'ordinary_registry' and row['category'] == 'literature_excluded' for row in entries)
source_files = set()
for g in GROUPS:
    for field in ('implementation', 'output_readers_or_calculators', 'evidence'):
        source_files.update(row['path'] for row in g[field])
source_files.update(row['path'] for row in grader_functions)
source_files.update(['docs/TOOL_KNOWLEDGE.md', 'docs/BLAST_TOOL_GRADERS.md',
    'gene_annotation_episode/scientific_tool_library.py', 'gene_annotation_episode/scientific_tool_retrieval.py',
    'gene_annotation_episode/tool_information.py', 'gene_annotation_episode/scientific_process_setup.py',
    'gene_annotation_episode/tool_configuration.py', 'gene_annotation_episode/episode_services.py',
    'gene_annotation_episode/runtime.py', 'gene_annotation_episode/composition_information.py',
    'gene_annotation_episode/scientific_process_episodes.py', 'gene_annotation_episode/execution_service_setup.py',
    'gene_annotation_episode/tool_knowledge.py', 'gene_annotation_episode/launch_instructions.py',
    'gene_annotation_episode/execution_inventory.py', 'tests/test_child_tool_information.py',
    'pyproject.toml', 'gene_annotation_episode/defaults.toml', 'resources/local-tools.toml',
    'verification/aurora_bioinformatics_2026-10-22_001/WORKSPACE_DIRECTORY.md'])
for row in manuals:
    source_files.add(row['manifest'])
    for section in row['sections']:
        source_files.add(str(Path(row['manifest']).parent/section['path']))
source_records = []
for name in sorted(source_files):
    p = ROOT/name
    source_records.append({'path': name, 'present': p.is_file(),
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None})

inventory = {
    'version': 'current_application_tool_grader_inventory_v1',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'root': str(ROOT),
    'scope': 'Existing application tools, their actual local/API/HPC boundaries, readers, and tool-grader integration. Separate from BV-BRC upstream and reference/episode_tools inventories; literature graders excluded.',
    'method': {'performed': ['Read source/docs/manifests', 'Evaluate declared schema/metadata builders',
        'Read package distribution metadata and file presence', 'Pure in-memory resolver diagnostic'],
        'not_performed': ['Network requests', 'SSH/authentication', 'Native bioinformatics execution', 'Test suite',
            'Scientific/model episode', 'Source/old-doc edit', 'Scorer implementation', 'Axis formula or execution behavior change'],
        'runtime_configuration_note': 'Catalog contracts are extracted without Store construction. Per-run availability/configuration fields appended by ToolRegistry.catalog are documented separately; no active caller/run was instantiated.'},
    'counts': {'ordinary_registry_base': ordinary_count, 'ordinary_registry_with_optional_execution_estimate': ordinary_count + 1,
        'ordinary_excluded_literature_document_entries': excluded, 'ordinary_nonliterature': ordinary_count-excluded,
        'resource_execution_variants': {k: len(v) for k, v in resource_catalogs.items()},
        'resource_execution_variants_total': sum(map(len, resource_catalogs.values())),
        'merged_base_name_resource_variants': len(entries), 'merged_base_unique_names': len({row['name'] for row in entries}),
        'merged_base_categories': dict(aux_counts), 'manual_entries': len(manuals),
        'native_algorithm_families_under_explicit_grouping': len(native_families),
        'additional_measurement_preparation_groups': ['sequence_composition', 'sequence_translation', 'sequence_views'],
        'resource_operations_are_not_grader_count': {'generic_file_shell_status_progress_variants': 36,
            'phmmer_and_blast_hmmer_algorithm_lifecycle_variants': 20, 'uniprot_bvbrc_data_retrieval_variants': 5},
        'implemented_tool_grader_families': 1, 'implemented_tool_sheet_types': 2,
        'automatic_production_tool_grader_bindings_found': 0},
    'entries': entries,
    'conditional_entries': [{**make_tool_info(conditional_contract, 'local'),
        'input_schema': conditional_contract['input_schema'], 'condition': 'ToolRegistry.native_statistics is not None',
        'category': 'infrastructure', 'scientific_grader_binding': 'not_a_scientific_grader',
        'definition': {'path': 'gene_annotation_episode/tools.py', 'line': conditional_assignment.lineno},
        'supported_estimates': ['sequence.align', 'source.xlsx.sheets', 'source.xlsx.rows']}],
    'groups': GROUPS, 'native_algorithm_families': native_families,
    'manual_libraries': manuals,
    'grader_functions': grader_functions,
    'grader_integration': {
        'existing': 'BLAST standalone Python facade/CLI builds pairwise/database sheets from retained bytes plus explicit metadata. No registry/resource automatic invocation found.',
        'input_contract': ['mode pairwise/database', 'resource api/local/hpc as provenance', 'json2 or declared tabular format',
            'optional recorded request, reference metadata, target context, database population, model parameters'],
        'native_publication_surfaces': locations(('gene_annotation_episode/tools.py', '_import_blast'),
            ('gene_annotation_episode/api_blast.py', 'publish'), ('gene_annotation_episode/tools.py', '_publish_hmmer_rows'),
            ('gene_annotation_episode/homology_results.py', 'extract'), ('gene_annotation_episode/tools.py', '_align_one'),
            ('gene_annotation_episode/tools.py', '_publish_read_alignments'), ('gene_annotation_episode/tools.py', '_publish_mapping'),
            ('gene_annotation_episode/tools.py', '_publish_cmsearch'), ('gene_annotation_episode/tools.py', '_derive'),
            ('gene_annotation_episode/tools.py', '_import_rfam_discovery')),
        'missing': ['No tool-to-reader/grader registry keyed by algorithm/native format and actual output witness.',
            'No production publication calls to grade_blast_result; caller must explicitly supply retained bytes and linked metadata.',
            'No populated tool-specific scoring sheet for Biopython alignment, Prodigal, minimap2, Infernal, local/API HMMER or Rfam.',
            'No automatic parser/grader selection for arbitrary practical local/HPC output files.',
            'No ordinary NCBI assembly-report acquisition/link resolver for BLAST assembly metadata.',
            'W05 axis/annotation-credit integration remains outside this inventory and must not be inferred from native measurements.'],
        'separation': 'Prompt instructions, scoring sheet/template, deterministic readers/calculators, and later W05 credit wiring remain separate. Data transport/file status is not a new scientific grader.'},
    'publication_and_ownership': {
        'four_field_builder': location('gene_annotation_episode/tool_information.py', 'make_tool_info'),
        'global_variant_collector': location('gene_annotation_episode/tool_information.py', 'workflow_execution_catalogs'),
        'frozen_loader': location('gene_annotation_episode/scientific_tool_library.py', 'ScientificToolLibrary'),
        'actual_setup': location('gene_annotation_episode/scientific_process_setup.py', 'prepare_scientific_binding'),
        'ordinary_registration': location('gene_annotation_episode/tools.py', 'catalog'),
        'ordinary_dispatch': location('gene_annotation_episode/tools.py', '_execute_operation_async'),
        'api_registration': location('gene_annotation_episode/api_services.py', 'build_service'),
        'execution_registration': location('gene_annotation_episode/execution_service_setup.py', 'ExecutionServiceFactory'),
        'root_restriction': location('gene_annotation_episode/composition_information.py', 'restricted_root'),
        'manual_delivery': 'ToolKnowledge/LaunchInstructions freeze per-run manifests, validate digests, and read explicit pages; launch.instructions.select pins section identities into launch assignment.',
        'tool_info_delivery': 'ScientificToolLibrary v2 freezes exact four-field rows and separate actual schemas. Parent sees name/description/resources; selected scientific child resolves full instructions/schema. Receiver binding remains authoritative.',
        'resource_information_not_direct_grant': 'The 61 execution declarations belong to resource/monitor/results owners. Keeping them out of ordinary scientific/root callable catalogs is intentional. The resource child needs its original assignment, not a wider root grant.',
        'active_publication_note': 'Tool information is generated at run construction rather than a standalone static active tool index. A/P source_directory is caller-owned: top-level research index has P19/A0; 2026-10-24-001 publication has A10/P19 and explicitly says no tool/scoring implementation.',
        'discovery_selection_diagnostic': diagnostic},
    'completeness_and_truncation': [
        'All 115 base declarations are included in this JSON, including 13 literature/document entries explicitly excluded from scientific-grader work.',
        'No fixed count truncation found in scientific_tool_library._tool_information, parent_tool_info, or ScientificToolRetriever.retrieve. Semantic selection can still omit relevant tools; literal retrieval has no relevance/completeness guarantee.',
        'Semantic scientific retrieval filters to the ordinary receiver map; the 61 execution rows remain global declarations for other owners. Literal runtime fallback omits that filter and can return a selection later rejected, as recorded.',
        'ToolKnowledge and LaunchInstructions searches/readers paginate with total/next_query, rather than silently truncating the complete library.',
        'Rfam/cmsearch/site/gene previews use 12 rows and chemistry uses 6; complete retained sources/records remain separate. These previews are not evidence of an exhaustive result set.',
        'BLAST installed client receives max_hits=12/max_queries=1 for its compact envelope, but PublicClients captures native HTTP entity bytes and the application parses those retained bytes. It does not grade the compact hit preview.',
        'All current manual tool_names have some actual declaration. Not every manual operation is bound to every episode, and generic fallback instructions are not complete software manuals.',
        'Historical T01-T13 research tool contexts live only under background/pre_curation_20261021; they are not current callable entries. Structural search/docking, tree construction, motif/kinetic/table analysis descriptions do not create implementations.',
        'Installed Infernal/HMMER/BLAST binaries without named bindings are listed separately. Presence does not supply an invocation contract, selected database, native-output importer or grader.',
        'Old docs cite validation/providers/rfam-native and rfam-batch-calibration, which are absent in this checkout; Rfam test module imports the absent batch fixture directly, while native RNA fixture discovery can skip. No test run was attempted.'
    ],
    'deployment': {
        'local': {'packages': packages, 'caller_configuration_sources': locations('resources/local-tools.toml', 'cases/gene_001/execution.toml',
            'gene_annotation_episode/defaults.toml', 'pyproject.toml'), 'binary_directory_facts': binary_dirs,
            'additional_files': [file_fact('resources/software/minimap2-2.31/source/minimap2-2.31/minimap2'),
                file_fact('cases/gene_001/jobs/homology_001/reviewed.fasta')],
            'path_commands': {name: shutil.which(name) for name in ('systemd-run','systemctl','prlimit','pdfinfo','pdftotext','pdftoppm','ssh','qsub','qstat','phmmer','cmsearch','minimap2','blastp')},
            'skill_client_files': skill_clients, 'ncbi_contact_present_value_not_disclosed': bool(ncbi_contact()),
            'current_user_systemd_cgroup_readiness': 'not probed',
            'unbound_binary_note': 'Only phmmer and cmsearch have dedicated HMMER/Infernal invocation adapters. BLAST+ local pairwise use is a verification helper; other listed programs have no dedicated current callable or tool grader.'},
        'aurora': {'status': 'Historical 2026-10-22 manual Gentner/Biopython global-alignment success; current availability/authentication and other software/databases unverified.',
            'recorded_job': '8953621.aurora-pbs-0001.hostmgmt.cm.aurora.alcf.anl.gov', 'comparisons': 17,
            'source_root': '/lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/repos/gentner-ave',
            'python': '/lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/venvs/gentner/bin/python',
            'recorded_versions': {'python': '3.12.12', 'biopython': '1.87', 'academy-py': '0.5.0', 'pydantic': '2.13.4'},
            'storage': '/lus/flare/projects/BioReason-Aurora-Test', 'new_pbs_account': 'EpiCalib',
            'historical_test_account': 'BioReason-Aurora-Test',
            'missing_or_unverified': ['No current authenticated session probed', 'No remote structured software inventory located in inspected sources',
                'No evidence that BLAST/HMMER/Infernal/minimap2 databases or binaries are installed there',
                'No full episodic HPC deployment established by the manual test', 'Arbitrary requested argv still needs algorithm-specific retained outputs and reader/grader binding'],
            'inventory_sources': locations('verification/aurora_bioinformatics_2026-10-22_001/WORKSPACE_DIRECTORY.md',
                'verification/aurora_bioinformatics_2026-10-22_001/execution.json', 'verification/aurora_bioinformatics_2026-10-22_001/README.md',
                'gene_annotation_episode/launch_instruction_library/aurora-software.md')},
        'polaris': {'status': 'Not exercised in the retained workspace index; no concrete software/resource inventory or caller binding located.',
            'missing': ['Exact resource configuration/access preparation', 'Installed software/database inventory', 'Native execution and result-parser verification'],
            'evidence': locations('verification/aurora_bioinformatics_2026-10-22_001/WORKSPACE_DIRECTORY.md', 'docs/AMENDMENTS/RESOURCE_EPISODE_CORRECTION_2026-10-22_001.md')},
        'spark': {'status': 'Separate non-HPC tailnet box is future direction; exact hostname unknown in retained direction and no deployment inventory located.',
            'missing': ['Exact hostname/access/resource binding', 'Installed software/database inventory', 'Native execution/result verification'],
            'evidence': locations('docs/AMENDMENTS/RESOURCE_EPISODE_CORRECTION_2026-10-22_001.md', 'verification/aurora_bioinformatics_2026-10-22_001/WORKSPACE_DIRECTORY.md')},
        'inventory_schema': {'location': location('gene_annotation_episode/execution_inventory.py', 'validate_component'),
            'meaning': 'Strict software/environment/database/prepared-operation catalog and mirrored snapshot. A prepared operation must match an actual tool name/input schema. Equal catalog hashes do not prove current usability.',
            'deployment_census_limit': 'Search was limited to repository/current source/docs, known verification receipts and external run filenames; no home-wide credential search or remote discovery.'}},
    'source_manifest': source_records,
}

out = Path(__file__).parent
(out/'current.json').write_text(json.dumps(inventory, indent=2, ensure_ascii=False, allow_nan=False)+'\n')

def link(source):
    return f"[{Path(source).name}](../../{source})"

lines = [
    '# Current application tool inventory — 2026-10-24', '',
    f"The existing application declares **{ordinary_count} ordinary operations** ({ordinary_count+1} with optional timing estimation) and **61 resource execution variants**: 27 local, 16 HPC, 18 API. The combined four-field map has **{len(entries)} name/resource rows** and **{len({r['name'] for r in entries})} unique names**. Thirteen ordinary literature/document operations are excluded here, leaving **{ordinary_count-excluded} ordinary non-literature operations**. Complete names, descriptions, resources, instructions, schemas and evidence are in [current.json](current.json).", '',
    'The 61 execution rows comprise **36 generic infrastructure variants**, **20 HMMER/phmmer/BLAST lifecycle variants**, and **5 UniProt/BV-BRC data retrieval variants**. Shell, file, status, prepare, collect and progress operations do not imply independent scientific graders.', '',
    '| Scientific algorithm family | Actual interface/resource | Existing grader and deployment limit |',
    '| --- | --- | --- |',
    '| Biopython pairwise alignment | `sequence.align`, `reads.align`; local | Native scores/identity/coverage exist; no tool sheet. Biopython 1.88 installed. Aurora proves only its earlier manual global-alignment test. |',
    '| Prodigal | `genes.predict`; local Pyrodigal meta/single | Native CDS/confidence/score; no tool sheet. Pyrodigal 3.7.1 installed. |',
    '| minimap2 | `reads.map`; local, six presets | PAF/cg/cs reader; no tool sheet. Binary 2.31-r1302 exists; executable is not selected by package/default local config. |',
    '| Infernal cmsearch | `rna.cmsearch`; local | fmt3/native source reader; no tool sheet. Binary 1.1.5 exists; requires explicit executable and selected CM. |',
    '| HMMER phmmer | local `homology.*`; API `api.hmmer.*` | Two native formats/readers; no tool sheet. Local pinned executable/reference FASTA exist. |',
    '| HMMER hmmscan | `api.hmmer.*`; API | API domain/coverage reader; no tool sheet. Local binary exists but no dedicated local callable. |',
    '| Rfam batch cmscan | `public.rfam.search/collect`; API | Native family/score/coordinate reader; no tool sheet. Historical calibration paths are missing here. |',
    '| BLAST | five programs through `public.blast.*`/`api.blast.*`; local test helper; HPC formats | **Two standalone sheets implemented**, with native and metadata readers. No production grader binding. Actual local pairwise test exists; saved live API checkpoint is WAITING/blocked; HPC execution unverified. |', '',
    'Additional deterministic measurements/preparations are sequence/read composition, translation, sequence views and translation-code lookup. Data readers include alignment sites/BLAST HSPs, GenBank neighborhoods, material FASTA/FASTQ/GenBank intake, original-read libraries, source/record windows, UniProt, NCBI sequence/search/taxonomy, Rfam models, Rhea, ChEBI, and BV-BRC genome/feature/protein-family pages. They retain source facts; transport alone is not a numerical scoring sheet.', '',
    'The current BLAST function boundary is '+link('gene_annotation_episode/blast_graders.py')+' → native readers → pairwise/database sheet builders → replaceable database calculator. It is only called by its CLI/tests/verification helpers in the inspected paths. Ordinary/API result publication retains data but never calls this facade. No other native algorithm has a dedicated sheet/grader binding; W05 remains separate.', '',
    'Publication runs through '+link('gene_annotation_episode/tool_information.py')+' (`make_tool_info`, `workflow_execution_catalogs`), '+link('gene_annotation_episode/scientific_tool_library.py')+' (run-frozen v2 rows/contracts), and '+link('gene_annotation_episode/scientific_process_setup.py')+'. There are 3 general manuals and 6 launch manuals. Current manual names have declarations, but reading a manual grants no execution capability. Generic fallback instruction text is not a full algorithm manual.', '',
    '**Ownership and selection:** the 61 execution rows belong to launch/resource/results/monitor owners. Keeping them out of direct scientific/root catalogs is correct. A pure metadata diagnostic reproduces a narrower inconsistency: runtime literal `process.tools("BLAST")` can return `{name: "api.blast.submit", resources: "api"}` without receiver filtering; scientific-child materialization then rejects it with `scientific_tool_contract_changed:api.blast.submit:api`. Semantic retrieval already filters. The proper integration is selected information → fixed launch/service assignment → resource child execution; it must preserve root restrictions.', '',
    'No numeric catalog truncation was found in the current tool-map loader or retriever. Search/manual pages expose continuation; result previews (12 rows, or 6 for chemistry) are bounded views of retained data. Historical T01–T13 research bundles are background, not actual tools. Installed extra Infernal/HMMER/BLAST executables and PyHMMER do not acquire bindings merely by being present.', '',
    '**Resources:** local package versions, binary paths, installed skill-client paths and explicit-config gaps are recorded in JSON. Aurora inventory is the retained '+link('verification/aurora_bioinformatics_2026-10-22_001/WORKSPACE_DIRECTORY.md')+' and execution receipt: Gentner/Biopython returned 17 pairwise comparisons on 2026-10-22. It proves no other HPC algorithm/database or current authentication. Polaris has not been exercised; Spark remains a separate non-HPC host with unknown hostname in retained direction. No concrete deployment inventory for either was located.', '',
    '**Verification performed:** source/schema/manifest inspection, package/file metadata reads, and the pure resolver diagnostic only. No scientific tool, network/API request, SSH/authentication, native job, model episode or test suite was run. Only `current.*` inventory artifacts were written. Existing source, historical receipts, scoring formulas, prompts and execution behavior were unchanged.',
]
(out/'current.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'output': [str(out/'current.json'), str(out/'current.md')], 'counts': inventory['counts'],
    'resolver_failure': failure, 'source_files': len(source_records)}, indent=2))
