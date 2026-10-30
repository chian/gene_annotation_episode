"""Static inventory only. Does not import or execute Gentner/Biomni algorithms.

Rebuild with python3 research/tool_grader_inventory_2026-10-24/gentner.inventory.py.
The two output artifacts describe the inspected checkout, not a deployment test.
"""
from __future__ import annotations

import ast
import builtins
import collections
import hashlib
import json
import re
import shutil
import symtable
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent
GENTNER = ROOT / "reference/episode_tools"
SITE = GENTNER / ".venv/lib/python3.12/site-packages"
BIOMNI = SITE / "biomni"
SOURCE = BIOMNI / "tool"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}


def ref(path, line=1):
    return {"path": str(path.relative_to(ROOT)), "line": line}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def extract_literal(path, variable):
    tree = ast.parse(path.read_text())
    for n in tree.body:
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if any(isinstance(t, ast.Name) and t.id == variable for t in targets):
                return ast.literal_eval(n.value)
    raise ValueError((path, variable))


EXCLUDED = {
    "annotate_celltype_scRNA": ("excluded_llm", "Cell-type labels are composed by a language model; this is not a deterministic annotation algorithm or grader."),
    "query_chatnt": ("excluded_llm", "Sequence-conditioned generated English from a transformer pipeline; no structured numerical biological result contract."),
    "list_glycoengineering_resources": ("excluded_discovery", "Curated external links are resource information, not executed glycosylation algorithms."),
    "run_python_repl": ("excluded_execution", "Arbitrary-code runner; the submitted computation would need its own native-result contract."),
    "read_function_source_code": ("excluded_discovery", "Code inspection helper."),
    "get_captured_plots": ("excluded_presentation", "Returns captured presentation artifacts."),
    "clear_captured_plots": ("excluded_presentation", "Clears presentation state."),
    "create_segmentation_visualization": ("excluded_presentation", "Plots existing segmentation; does not create independent biological measurements."),
    "create_registration_visualization": ("excluded_missing", "Advertised catalog function has no module-level implementation; the referenced class visualization method is also absent."),
    "get_oligo_annealing_protocol": ("excluded_protocol", "Wet-lab instruction text, not an observed or predicted biological result."),
    "get_golden_gate_assembly_protocol": ("excluded_protocol", "Wet-lab protocol and reaction-amount arithmetic; distinct from sequence assembly prediction."),
    "get_bacterial_transformation_protocol": ("excluded_protocol", "Wet-lab instruction text."),
    "run_3d_chondrogenic_aggregate_assay": ("excluded_protocol", "Produces an assay protocol, not assay observations."),
    "analyze_enzyme_kinetics_assay": ("excluded_mock_experiment", "Creates activities from fixed true_vmax=120 and true_km=25 plus random noise, and random modulator IC50; no measured activity input."),
    "perform_crispr_cas9_genome_editing": ("excluded_mock_experiment", "Scores GC/PAM with fixed categories, looks up assumed delivery efficiencies, and generates a random deletion; not measured editing or a validated predictor."),
    "isolate_purify_immune_cells": ("excluded_mock_experiment", "Generates random cell counts, purity and viability from tissue/cell labels rather than observations."),
    "enumerate_bacterial_cfu_by_serial_dilution": ("excluded_mock_experiment", "Generates Poisson colony counts from an assumed concentration; cannot grade measured CFU data because none are accepted."),
    "analyze_accelerated_stability_of_pharmaceutical_formulations": ("excluded_mock_experiment", "Generates stability using fixed degradation and physical-score formulas; no measured stability input or fitted formulation-specific parameters."),
}

DATA_READERS = {
    "get_hpo_names", "get_gene_coding_sequence", "get_plasmid_sequence", "design_knockout_sgrna",
    "interspecies_gene_conversion", "get_rna_seq_archs4", "get_gene_set_enrichment_analysis_supported_database_list",
    "download_synapse_data", "get_genes_near_ccre", "region_to_ccre_screen",
    "query_drug_interactions", "check_drug_combination_safety", "analyze_interaction_mechanisms",
    "find_alternative_drugs_ddinter", "query_fda_adverse_events", "get_fda_drug_label_info", "check_fda_drug_recalls",
}

PREPARATION = {"split_modalities", "prepare_input_for_nnunet", "preprocess_image", "create_biochemical_network_sbml_model"}
SIMULATIONS = {
    "simulate_whole_cell_ode_model", "simulate_demographic_history", "perform_pcr_and_gel_electrophoresis",
    "optimize_anaerobic_digestion_process", "model_bacterial_growth_dynamics", "simulate_generalized_lotka_volterra_dynamics",
    "simulate_microbial_population_dynamics", "simulate_thyroid_hormone_pharmacokinetics", "simulate_gene_circuit_with_growth_feedback",
    "model_protein_dimerization_network", "simulate_metabolic_network_perturbation", "simulate_protein_signaling_network",
    "simulate_renin_angiotensin_system_dynamics",
}

NOTES = {
    "blast_sequence": ["NCBIWWW.qblast remote XML path only, fixed expect=100, word_size=7, megablast=True; returns the first HSP of the first hit, discarding other HSPs/hits and the raw XML.", "Reported coverage is len(hsp.query)/len(input sequence)*100, which counts alignment-string characters rather than gap-resolved paired residues. Existing blast_graders need retained native results, not this lossy summary."],
    "analyze_protein_conservation": ["MUSCLE failure triggers right-padding input sequences to equal length, then constructs an identity-distance NJ tree; this fallback is not an MSA.", "Conservation includes gaps in the most-common-character fraction and writes values rounded to two decimals."],
    "analyze_protein_phylogeny": ["Default tree_method='fasttree' is not implemented: the tree-building branch accepts iqtree and rejects other values. Failed IQ-TREE/alignment fallback can write a fixed four-leaf placeholder Newick tree. Selected method, actual fallback and source sequences must be retained.", "Imports Bio.Align.Applications, absent from the inspected reference virtual environment; source presence is not callable availability."],
    "analyze_comparative_genomics_and_haplotypes": ["Partially implemented: BWA alignment can be real, but BWA-success variants are a placeholder string; fallback compares at most ten base differences by same record ID. Haplotype groups use sample index modulo 3, with random variant counts and divergence times. These haplotype numbers are not scientific results."],
    "analyze_cfse_cell_proliferation": ["Real FCS branch exists; missing FlowCytometryTools generates mock populations, while read/gating errors substitute division_index=1.2 and percent_proliferating=65.0. Both synthetic branches must be marked non-observational."],
    "track_immune_cells_under_flow": ["Image-loading and tracking failures can substitute dummy images and simulated tracks; retain branch provenance before scoring trajectory metrics."],
    "analyze_cns_lesion_histology": ["Missing scikit-image or image-processing failure substitutes stain-specific simulated metrics; retain branch provenance and do not grade them as image measurements."],
    "analyze_chromatin_interactions": ["Failed representative-matrix acquisition can save a zero-valued 10x10 placeholder. Balanced/unbalanced matrix fallback and empty outputs need explicit provenance."],
    "detect_and_characterize_structural_variations": ["LUMPY calling is implemented, but requested COSMIC/ClinVar annotation step is explicitly simulated. The split-read shell pipeline is passed as a list with shell=True and needs execution repair/verification."],
    "analyze_cell_senescence_and_apoptosis": ["Missing marker channels can be replaced by arbitrary available fluorescence channels; those labels do not establish marker-specific measurements."],
    "analyze_copy_number_purity_ploidy_and_focal_events": ["CNVkit outputs coexist with approximate purity/ploidy and threshold-defined focal events; preserve exact calculation method and do not present approximations as an independent caller."],
    "find_n_glycosylation_motifs": ["Canonical sequon occurrence is a sequence calculation, not observed glycosylation."],
    "predict_o_glycosylation_hotspots": ["Explicit lightweight S/T-density heuristic, not NetOGlyc, a fitted predictor, or experimental occupancy."],
    "identify_fas_functional_domains": ["Remote Pfam search and FAS-specific domain interpretation; do not equate generic domain matches with demonstrated fatty-acid synthase function."],
    "grade_adverse_events_using_vcog_ctcae": ["Domain-specific clinical rule arithmetic includes a default Grade 1 for missing criteria and category-to-grade mappings. These source grades are not an evidence-reliability or annotation-credit model."],
    "run_diffdock_with_smiles": ["Implementation automatically pulls Docker images; Docker/NVIDIA runtime and compatible GPU are deployment prerequisites. No container was pulled for inventory."],
    "predict_admet_properties": ["Implementation may invoke pip to install DeepPurpose and download model weights during a call. No installation was performed."],
    "predict_binding_affinity_protein_1d_sequence": ["Implementation may invoke pip to install DeepPurpose and download model weights during a call. No installation was performed."],
    "annotate_celltype_with_panhumanpy": ["Implementation creates a Python 3.10 conda environment and installs panhumanpy from GitHub if needed. No environment was created."],
    "get_uce_embeddings_scRNA": ["Depends on external UCE source/scripts and model/data files under an explicit DATA_ROOT, default /dfs/project/bioagentos/data/singlecell/. Presence of the Python wrapper does not establish these assets."],
    "map_to_ima_interpret_scRNA": ["Requires external atlas embeddings/labels and compatible precomputed query embedding space; output probabilities/distances are not annotation-correctness probabilities."],
    "generate_embeddings_with_state": ["May clone large SE-600M weights through git-lfs; requires state CLI/package and compatible compute stack."],
    "generate_transcriptformer_embeddings": ["May download model checkpoints through transcriptformer CLI; GPU and package/checkpoint compatibility remain unverified."],
    "segment_with_nn_unet": ["Depends on nnUNet v1 API, model weights and compatible PyTorch; implementation may download weights and patches torch.load."],
    "quick_rigid_registration": ["Default create_visualizations=True references a missing ImageRegistrationTool.create_registration_visualization method; scientific registration and metric outputs must be isolated/verified."],
    "quick_affine_registration": ["Default create_visualizations=True references a missing ImageRegistrationTool.create_registration_visualization method."],
    "quick_deformable_registration": ["Default create_visualizations=True references a missing ImageRegistrationTool.create_registration_visualization method."],
    "batch_register_images": ["Uses the same registration wrappers; their default visualization-method failure applies to this batch surface."],
    "compare_protein_structures": ["Compares CA atoms matched by residue IDs in selected chains, not a general sequence-aligned structural homology search or TM-align."],
    "perform_pcr_and_gel_electrophoresis": ["In-silico PCR/gel simulation; produced band/intensity image is not measured electrophoresis."],
    "optimize_anaerobic_digestion_process": ["Optimization operates on the function's assumed process model; fitted empirical validation is not supplied by a label or optimizer success."],
    "analyze_fda_safety_signals": ["Uses actual retrieved adverse-event aggregates when available; comparative signal arithmetic is not causal adverse-event attribution or a clinical recommendation."],
}


def classify(module, name, function):
    if name in EXCLUDED:
        return EXCLUDED[name]
    if module.endswith("literature"):
        return "excluded_literature", "Literature/web search, page/PDF extraction, or literature-agent helper excluded by task scope."
    if module.endswith("lab_automation"):
        return "excluded_lab_automation", "Robot documentation or arbitrary laboratory-script test, not a native biological-result algorithm."
    if function is None:
        return "excluded_missing", "Registered name has no callable implementation in the inspected module."
    if name in DATA_READERS or (module.endswith("database") and name != "blast_sequence"):
        return "biological_data_reader", "Retrieves, maps, filters or summarizes source records; keeps source meaning distinct from algorithmic annotation evidence."
    if name in PREPARATION:
        return "biological_data_preparation", "Concrete biological data/model format transformation supporting an algorithm."
    if name in SIMULATIONS:
        return "scientific_model_simulation", "Computes model predictions from supplied or explicitly defaulted model parameters; not observed biology."
    return "scientific_algorithm", "Concrete analysis of supplied data or an explicit predictive model; implementation validity and deployment remain separately qualified."


def package_presence(root):
    if root in STDLIB:
        return {"root": root, "reference_environment": "python_standard_library"}
    candidates = [SITE / root, SITE / (root + ".py")]
    candidates.extend(SITE.glob(root + ".*.so"))
    found = next((p for p in candidates if p.exists()), None)
    return {"root": root, "reference_environment": "source_or_binary_present_unimported" if found else "not_found_in_inspected_site_packages", "path": str(found.relative_to(ROOT)) if found else None}


def import_module_presence(name):
    root = name.split('.')[0]
    if root in STDLIB:
        return {"module": name, "status": "standard_library_root"}
    p = SITE.joinpath(*name.split('.'))
    candidates = [p, p.with_suffix('.py')]
    candidates.extend(p.parent.glob(p.name + ".*.so"))
    found = next((x for x in candidates if x.exists()), None)
    return {"module": name, "status": "source_or_binary_present_unimported" if found else "not_found_as_static_module_path", "path": str(found.relative_to(ROOT)) if found else None}


def imports(nodes):
    result = []
    for top in nodes:
        for n in ast.walk(top):
            if isinstance(n, ast.Import):
                for a in n.names:
                    result.append({"module": a.name, "root": a.name.split('.')[0], "line": n.lineno})
            elif isinstance(n, ast.ImportFrom) and n.module:
                result.append({"module": n.module, "root": n.module.split('.')[0], "names": [a.name for a in n.names], "line": n.lineno})
    return result


def file_data(path):
    source = path.read_text()
    tree = ast.parse(source)
    return {
        "path": path, "text": source, "tree": tree,
        "functions": {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))},
        "classes": {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)},
        "global_imports": imports(n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))),
        "symtable": symtable.symtable(source, str(path), "exec"),
    }


def reachable(fd, f):
    selected = {f.name: f}
    while True:
        old = len(selected)
        for node in list(selected.values()):
            for c in ast.walk(node):
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name):
                    candidate = fd["functions"].get(c.func.id) or fd["classes"].get(c.func.id)
                    if candidate:
                        selected[c.func.id] = candidate
        if old == len(selected):
            return selected


def function_facts(fd, f):
    closure = reachable(fd, f)
    nodes = list(closure.values())
    all_imports = fd["global_imports"] + imports(nodes)
    calls, returns, artifacts, assignments, commands, urls, warnings = [], [], [], [], [], [], []
    for node in nodes:
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                key = ast.unparse(n.func)
                item = {"line": n.lineno, "expression": ast.unparse(n)}
                calls.append({"line": n.lineno, "callable": key})
                if any(x in key for x in ("subprocess.", "os.system", "os.popen", "Commandline")):
                    commands.append(item)
                if (re.search(r"\.(write|writerow|writerows|to_csv|to_hdf|to_excel|to_pickle|save|savez|savetxt|savefig|imsave|write_h5ad|write_vcf|writeSBMLToFile)$", key)
                        or key in {"json.dump", "pickle.dump", "open"}):
                    artifacts.append(item)
            elif isinstance(n, ast.Return) and n.value is not None:
                returns.append({"line": n.lineno, "expression": ast.unparse(n.value)})
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                assignments.append({"line": n.lineno, "expression": ast.unparse(n)})
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                urls.extend(re.findall(r"https?://[^\s\"<>]+", n.value))
    text_lines = fd["text"].splitlines()
    for node in nodes:
        for line, text in enumerate(text_lines[node.lineno - 1:node.end_lineno], node.lineno):
            if re.search(r"mock|placeholder|dummy|fallback|simulated analysis|simulated tracks|simulated variant|random\.", text, re.I):
                warnings.append({"line": line, "text": text.strip()})
    bound = {s.get_name() for s in fd["symtable"].get_symbols() if s.is_assigned() or s.is_imported() or s.is_namespace()}
    unresolved = set()
    for st in fd["symtable"].get_children():
        if st.get_name() != f.name:
            continue
        stack = [st]
        while stack:
            child = stack.pop()
            stack.extend(child.get_children())
            for s in child.get_symbols():
                if s.is_referenced() and s.is_global() and s.get_name() not in bound and s.get_name() not in {"__file__", "__name__", "__package__", "__spec__"} and not hasattr(builtins, s.get_name()):
                    unresolved.add(s.get_name())
    source = "\n".join(text_lines[f.lineno - 1:f.end_lineno])
    roots = sorted({i["root"] for i in all_imports})
    doc = ast.get_docstring(f) or ""
    output_doc = re.split(r"\n\s*(?:Returns|Return|Output|Outputs)\s*:?\s*\n", doc, maxsplit=1)
    output_doc = output_doc[1] if len(output_doc) == 2 else None
    format_evidence = []
    format_patterns = {
        "FASTA": r"fasta|\.faa\b|\.fna\b", "FASTQ": r"fastq", "GenBank": r"genbank|\.gbk\b|\.gbff\b",
        "GFF": r"\bgff3?\b", "BED": r"\.bed\b|\bBED\b|narrowPeak|broadPeak", "SAM/BAM": r"\b[BbSs][Aa][Mm]\b",
        "VCF": r"\bvcf\b", "Newick": r"newick|treefile", "Clustal": r"clustal", "PDB/PDBQT": r"pdbqt|\bpdb\b",
        "SMILES": r"smiles", "SDF": r"\.sdf\b|\bSDF\b", "CSV": r"\.csv\b|to_csv", "TSV": r"\.tsv\b|tab-delimited",
        "JSON": r"json", "XML/SBML": r"\.xml\b|\bsbml\b|retmode=.*xml", "AnnData/H5AD": r"h5ad|anndata",
        "NumPy arrays": r"\.npy\b|\.npz\b|np\.save", "Parquet": r"parquet", "FCS": r"\.fcs\b|\bFCS\b",
        "NIfTI": r"nifti|\.nii\b", "TIFF": r"tiff|\.tif\b", "PNG/JPEG image": r"\.png\b|\.jpg\b|\.jpeg\b",
        "PDF plot": r"\.pdf\b", "GraphML": r"graphml", "Plain-text report": r"research log|\.txt\b|detailed.*log",
        "Python pickle": r"pickle|\.pkl\b", "Cooler/Hi-C": r"cooler|\.cool\b|\.hic\b", "OBJ mesh": r"\.obj\b",
    }
    for fmt, pattern in format_patterns.items():
        for line_no, text in enumerate(text_lines[f.lineno - 1:f.end_lineno], f.lineno):
            if re.search(pattern, text, re.I):
                format_evidence.append({"format": fmt, "line": line_no, "source_text": text.strip()})
                break
    return {
        "callable_signature": f"{f.name}({ast.unparse(f.args)})" + (" -> " + ast.unparse(f.returns) if f.returns else ""),
        "implementation_source": {**ref(fd["path"], f.lineno), "end_line": f.end_lineno, "sha256": sha(source)},
        "implementation_docstring": ast.get_docstring(f),
        "input_contract": {"signature": ast.unparse(f.args), "details": "Exact argument schema is catalog_schema; full native docstring above declares input units/shapes and formats when present. Undocumented constraints remain unknown."},
        "output_contract": {"native_return_annotation": ast.unparse(f.returns) if f.returns else None, "native_documented_return_section": output_doc, "formats_mentioned_in_actual_function": format_evidence, "format_evidence_note": "Source-grounded format mentions can describe input, output or optional branches. Actual returned values and artifact writes/paths are retained separately; a mentioned format is not a successful production claim."},
        "reachable_same_module_implementations": [{"name": n, **ref(fd["path"], v.lineno), "end_line": v.end_lineno} for n, v in closure.items() if n != f.name],
        "python_imports": all_imports,
        "python_prerequisites": [package_presence(x) for x in roots],
        "import_module_filesystem_presence": [import_module_presence(x) for x in sorted({i['module'] for i in all_imports})],
        "unresolved_global_names_static": sorted(unresolved),
        "native_calls": calls,
        "return_expressions_including_nested_helpers": returns,
        "native_artifact_write_expressions": artifacts,
        "native_assignments_including_output_paths_and_calculations": assignments,
        "command_invocations": commands,
        "literal_endpoint_and_download_urls": sorted(set(urls)),
        "fallback_mock_and_randomness_source_lines": warnings,
    }


def resource_routes(record):
    """Keep computation placement separate from source/model acquisition.

    This is a reviewed resource description, not an inference from a URL or the
    broad AST helper closure (which includes whole classes for dependency audit).
    Library internals and deployments remain unverified unless stated here.
    """
    name, module, classification = record['name'], record['module'], record['classification']
    source = record.get('implementation_source')
    evidence = [source] if source else []
    computation = {
        'placement': 'worker_process_or_local_subprocess',
        'local_stage': 'Native Python operations and/or selected local library/CLI calls in the execution worker. Dependency-internal behavior and runtime compatibility remain unverified.',
        'remote_scientific_stage': None,
        'api_algorithm_implementation': 'No distinct remote scientific-computation implementation identified in the inspected wrapper; delegated library internals are not thereby proved offline.',
        'live_execution_verified': False,
    }
    inputs = {
        'mode': 'supplied_inputs_or_local_assets',
        'details': 'Caller-supplied arguments/files and explicitly referenced local source data; required assets are not proved present by a description.',
        'live_acquisition_verified': False,
    }
    models = {
        'mode': 'prerequisites_and_delegated_loading_unverified',
        'details': 'See per-tool imports, commands and asset paths. Any nested library download behavior not explicitly described below remains unverified.',
        'live_acquisition_verified': False,
    }
    if classification.startswith('excluded'):
        computation.update(placement='outside_scientific_algorithm_scope', local_stage='Excluded helper, instruction, presentation, LLM or mock-experiment surface; no biological algorithm-placement claim.', api_algorithm_implementation='Not counted as a scientific algorithm.')
    elif classification == 'biological_data_reader':
        computation.update(placement='source_reader_with_local_processing', local_stage='Source parsing, mapping, filtering or summarization in the worker; this row does not establish a separate scientific inference algorithm.', api_algorithm_implementation='Source retrieval is recorded under input_acquisition; it is not automatically remote execution of a scientific algorithm.')

    is_database_reader = module == 'biomni.tool.database' and name != 'get_hpo_names' and name != 'blast_sequence'
    is_gentner_remote_reader = (module == 'gentner_ave.tools.online_queries' and not classification.startswith('excluded')) or module == 'gentner_ave.tools.ncbi'
    fda_reader = name in {'query_fda_adverse_events', 'get_fda_drug_label_info', 'check_fda_drug_recalls'} or '.OpenFDAClient' in module
    remote_source_names = {'interspecies_gene_conversion', 'get_rna_seq_archs4', 'get_gene_set_enrichment_analysis_supported_database_list', 'get_gene_coding_sequence', 'get_plasmid_sequence', 'download_synapse_data', 'download_geo_series'}
    if is_database_reader or is_gentner_remote_reader or fda_reader or name in remote_source_names:
        inputs.update(mode='remote_source_data_or_catalog', details='API/remote data-source acquisition is implemented directly or delegated to the named source library. Parsing, filtering and formatting occur in the worker. Source service operations may depend on the requested endpoint; no unrequested algorithm deployment is inferred.')
        models.update(mode='no_model_inference_established_for_reader', details='Source reader prerequisites remain required; downloaded structures, tables or source annotations are data, not proof that this wrapper executes their producing model.')
    if name == 'query_reactome' and not classification.startswith('excluded'):
        inputs['details'] = 'Retrieves Reactome ContentService or a supplied AnalysisService URL via GET. The inspected wrapper has no gene-list POST analysis-submission path; an AnalysisService base URL alone does not establish implemented enrichment computation.'
    if name in {'query_pdb', 'query_chembl', 'query_stringdb'} and not classification.startswith('excluded'):
        computation['api_algorithm_implementation'] = 'Endpoint/query-dependent source-service operation. A similarity search or enrichment endpoint may ask the provider to compute results, but this generic reader does not establish an additional fixed scientific algorithm or its deployed availability.'

    if name in {'split_modalities', 'prepare_input_for_nnunet'}:
        computation.update(placement='worker_process', local_stage='Local NIfTI loading, modality splitting and/or file copying; no remote scientific calculation.', api_algorithm_implementation='No scientific API route in this operation.')
        inputs.update(mode='supplied_local_nifti', details='Reads caller-supplied local NIfTI file(s).')
        models.update(mode='no_model_used', details='This preparation operation does not load or download model weights. Zenodo URLs in the broad SegmentationTool class closure belong to a different method.')
        evidence.append(ref(SOURCE / 'bioimaging.py', 41 if name == 'split_modalities' else 87))
    elif name == 'segment_with_nn_unet':
        computation.update(placement='worker_process_local_model_inference', local_stage='Calls nnunet.inference.predict.predict_from_folder against locally accessible model files and NIfTI inputs in the worker.', api_algorithm_implementation='No remote segmentation API is implemented by this wrapper.')
        inputs.update(mode='supplied_local_nifti', details='Caller-supplied images; optional preparation remains local.')
        models.update(mode='local_weights_with_conditional_remote_download', details='Checks local nnUNet model/plan files; if missing, may download a Zenodo ZIP and extract it locally. Zenodo supplies weights, not remote inference. Model compatibility and download success unverified.')
        evidence.extend([ref(SOURCE / 'bioimaging.py', 225), ref(SOURCE / 'bioimaging.py', 278), ref(SOURCE / 'bioimaging.py', 438)])
    elif name == 'identify_transcription_factor_binding_sites':
        computation.update(placement='worker_process', local_stage='Biopython builds/scans a PSSM over the supplied sequence and calculates site scores in the worker.', api_algorithm_implementation='No remote TF-binding-site scan API is implemented.')
        inputs.update(mode='supplied_sequence_plus_remote_motif_data', details='Fetches a JASPAR matrix/PFM, then scans locally. The JASPAR request is motif-data acquisition.')
        models.update(mode='remote_source_motif_matrix', details='JASPAR motif data act as scoring input; no remote execution is inferred from obtaining the PFM.')
        evidence.extend([ref(SOURCE / 'genetics.py', 887), ref(SOURCE / 'genetics.py', 923)])
    elif name == 'generate_gene_embeddings_with_ESM_models':
        computation.update(placement='worker_process_local_model_inference', local_stage='ESM forward passes and isoform embedding averages execute through PyTorch in the worker on selected CPU/CUDA device.', api_algorithm_implementation='No remote ESM inference API is implemented.')
        inputs.update(mode='remote_sequence_acquisition', details='Fetches protein isoform FASTA from Ensembl before inference; Ensembl is the sequence source.')
        models.update(mode='delegated_model_load_possible_download', details='esm.pretrained.load_model_and_alphabet loads named ESM weights; cache/download behavior belongs to the dependency and is not verified in this environment. Loading weights does not move inference to the model host.')
        evidence.extend([ref(SOURCE / 'genomics.py', 284), ref(SOURCE / 'genomics.py', 343), ref(SOURCE / 'genomics.py', 386)])
    elif name == 'analyze_fda_safety_signals':
        computation.update(placement='worker_process', local_stage='Collects responses and runs _extract_fda_safety_signals / summary arithmetic in the worker.', api_algorithm_implementation='OpenFDA supplies source reports; the wrapper does not submit the comparative signal calculation to a scientific-compute API.')
        inputs.update(mode='remote_adverse_event_data', details='OpenFDAClient queries source adverse-event records; local calculations use those responses.')
        evidence.append(ref(SOURCE / 'pharmacology.py', 3741))
    elif name in {'blast_sequence', 'predict_protein_disorder_regions', 'identify_fas_functional_domains'}:
        service = {'blast_sequence': 'NCBI BLAST through NCBIWWW.qblast', 'predict_protein_disorder_regions': 'IUPred2A sequence submission', 'identify_fas_functional_domains': 'EBI HMMER hmmscan against Pfam'}[name]
        computation.update(placement='remote_scientific_service_with_local_postprocessing', local_stage='Sequence preparation plus native-response parsing/filtering/summary generation in the worker.', remote_scientific_stage=service, api_algorithm_implementation='Concrete sequence-analysis request is submitted to ' + service + '; live service, authentication/limits and response correctness remain untested.')
        inputs.update(mode='caller_sequence_service_reference_data', details='Caller supplies the sequence; the requested service performs analysis using its own algorithm/reference data.')
        models.update(mode='service_owned_algorithm_or_database', details='No local installation of the remote algorithm/database is established by this wrapper.')
    elif name in {'gene_set_enrichment_analysis', 'analyze_ddr_network_in_cancer'}:
        delegated = 'gget.enrichr' if name == 'gene_set_enrichment_analysis' else 'gseapy.enrichr'
        computation.update(placement='remote_analysis_via_library_with_local_processing', local_stage='Local preparation and result formatting/filtering' + (' plus expression/network/community analysis.' if name == 'analyze_ddr_network_in_cancer' else '.'), remote_scientific_stage='Enrichr analysis via ' + delegated, api_algorithm_implementation='The wrapper delegates a named-library gene-list enrichment request to ' + delegated + '. Primary upstream library source shows the remote Enrichr analysis path; the library is absent from the inspected environments, so the exact installed-version path and live execution are unverified.')
        inputs.update(mode='caller_gene_list_or_expression_inputs', details='Caller inputs are processed locally before the delegated Enrichr request; gene-set reference data belong to the requested enrichment library/service.')
        models.update(mode='missing_delegated_analysis_library', details=delegated.split('.')[0] + ' is not present in either inspected site-packages directory. No dependency or dataset was installed.')
        evidence.append({'url': 'https://raw.githubusercontent.com/pachterlab/gget/main/gget/gget_enrichr.py' if name == 'gene_set_enrichment_analysis' else 'https://raw.githubusercontent.com/zqfang/GSEApy/master/gseapy/enrichr.py', 'qualification': 'Current primary upstream source inspected on 2026-10-24; not asserted to be an installed or pinned dependency version.'})
    elif name in {'run_diffdock_with_smiles', 'predict_admet_properties', 'predict_binding_affinity_protein_1d_sequence', 'annotate_celltype_with_panhumanpy', 'generate_embeddings_with_state', 'generate_transcriptformer_embeddings'}:
        models.update(mode='local_execution_with_conditional_software_or_weight_acquisition', details='The wrapper may install/download software, container images or model files before local worker/subprocess inference. These acquisition operations do not establish a remote scientific-compute API. See exact native commands and reviewed qualifications.')
        computation['api_algorithm_implementation'] = 'No remote inference API identified in this wrapper; local delegated software/container behavior and compatible resources remain unverified.'

    transport = {
        'local_worker': 'Gentner has an Academy thread executor; local means computation in its selected worker process or subprocess, not a claim that this machine can run the tool.',
        'globus_parsl': 'Generic Globus/Parsl transports exist; actual endpoint/provider, authentication, environment, shared files and allocation must be supplied and verified.',
        'hpc_deployment_verified': False,
        'hpc_note': 'No tool-specific HPC deployment is established. Default Parsl uses LocalProvider. URLs, source availability and transport adapters do not prove HPC execution.',
    }
    return {
        'algorithm_execution': computation,
        'input_acquisition': inputs,
        'model_and_software_acquisition': models,
        'generic_transport': transport,
        'resource_evidence': evidence,
        'local': computation['local_stage'],
        'api': computation['api_algorithm_implementation'],
        'hpc': transport['hpc_note'],
        'executed_for_inventory': False,
        'optional_natural_language_api_query_builder': any(x['callable'] == '_query_llm_for_api' for x in record.get('native_calls', [])),
        'network_signal_scope_note': 'literal_endpoint_and_download_urls and broad same-class dependency closures are source-discovery evidence only; they do not determine algorithm placement.',
    }


def make_record(module, name, fd, schema=None, catalog_ref=None, kind="biomni_native"):
    f = fd["functions"].get(name)
    classification, reason = classify(module, name, f)
    record = {
        "id": module + "." + name, "module": module, "name": name, "surface": kind,
        "registered_in_biomni_catalog": schema is not None,
        "classification": classification, "in_algorithm_or_data_reader_scope": not classification.startswith("excluded"),
        "scope_reason": reason,
        "description": (schema or {}).get("description") or (ast.get_docstring(f) or "").split("\n")[0] if f else (schema or {}).get("description"),
        "catalog_schema": schema, "catalog_source": catalog_ref,
        "implementation_present": f is not None,
        "callable": module + "." + name,
        "reviewed_qualifications": NOTES.get(name, []),
        "future_grader_requirement": "Retain actual native bytes/objects and the exact executed branch, parameters and provenance; use deterministic source-field readers and explicit numerical calculators with stated units/denominators. No category-to-number evidence grade; a generated log, label or successful call is not a result or reliability probability.",
    }
    if f:
        facts = function_facts(fd, f)
        record.update(facts)
        record['execution_routes'] = resource_routes(record)
        record["missing_or_unverified_prerequisites"] = {
            "imports_not_found_in_reference_environment": [x["root"] for x in facts["python_prerequisites"] if x["reference_environment"].startswith("not_found")],
            "import_modules_not_found_as_static_paths": [x['module'] for x in facts['import_module_filesystem_presence'] if x['status'].startswith('not_found')],
            "unresolved_global_names": facts["unresolved_global_names_static"],
            "native_commands": "See exact command_invocations and native_assignments; present wrappers are not proof of executable versions or working command syntax.",
            "input_data_models_databases": "Caller must supply all required schema arguments and input assets/checkpoints/databases named by native paths and docstrings; existence was not assumed from descriptions.",
            "remote_service": "See execution_routes.algorithm_execution, input_acquisition and model_and_software_acquisition separately; no scientific service or acquisition was exercised, and delegated library behavior remains qualified.",
        }
    return record


def main():
    files = {p.stem: file_data(p) for p in SOURCE.glob("*.py") if p.stem not in {"__init__", "tool_registry"}}
    entries = []
    schema_names = {}
    for path in sorted((SOURCE / "tool_description").glob("*.py")):
        schemas = extract_literal(path, "description")
        schema_names[path.stem] = {s["name"] for s in schemas}
        ast_schema = next(n.value for n in ast.parse(path.read_text()).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "description" for t in n.targets))
        for schema, ast_item in zip(schemas, ast_schema.elts):
            entries.append(make_record("biomni.tool." + path.stem, schema["name"], files[path.stem], schema, ref(path, ast_item.lineno)))
    for module, fd in sorted(files.items()):
        for name in sorted(fd["functions"]):
            if not name.startswith("_") and name not in schema_names.get(module, set()):
                entries.append(make_record("biomni.tool." + module, name, fd))

    native_method_entries = []
    for module, fd in sorted(files.items()):
        for class_name, cls in fd['classes'].items():
            for method in cls.body:
                if not isinstance(method, ast.FunctionDef) or method.name.startswith('_'):
                    continue
                method_fd = {**fd, 'functions': {**fd['functions'], method.name: method}}
                r = make_record('biomni.tool.' + module + '.' + class_name, method.name, method_fd, kind='native_class_method')
                r['counting_note'] = 'Supporting native class operation; shared by registered top-level wrappers where present, not an additional registered tool or independent evidence contribution.'
                if method.name == 'load_image' or class_name == 'OpenFDAClient':
                    c = 'biological_data_reader'
                elif method.name in {'save_image', 'preprocess_image', 'split_modalities', 'prepare_input_for_nnunet', 'create_rigid_transform', 'create_affine_transform', 'create_deformable_transform'}:
                    c = 'biological_data_preparation'
                elif method.name in {'setup_nnunet_environment', 'setup_registration_method'}:
                    c = 'excluded_configuration'
                else:
                    c = r['classification']
                r.update(classification=c, in_algorithm_or_data_reader_scope=not c.startswith('excluded'))
                native_method_entries.append(r)

    gentner_entries = []
    for basename in ["online_queries", "ncbi", "data_lake", "literature", "biomni_catalog", "execution"]:
        path = GENTNER / "src/gentner_ave/tools" / (basename + ".py")
        fd = file_data(path)
        registered = set()
        if basename == "online_queries":
            for n in fd["tree"].body:
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "QUERY_TOOLS" for t in n.targets):
                    registered = {x.id for x in n.value.elts}
        for name, f in sorted(fd["functions"].items()):
            if name.startswith("_"):
                continue
            r = make_record("gentner_ave.tools." + basename, name, fd, kind="gentner_owned")
            if basename == "literature" or name in {"query_pubmed", "query_arxiv", "query_scholar", "search_google"}:
                c, reason = "excluded_literature", "Literature/web helper excluded by task scope."
            elif basename in {"biomni_catalog", "execution"} or name == "data_lake_one_liners":
                c, reason = "excluded_execution_or_discovery", "Catalog lookup, metadata description, or general code runner; not a scientific algorithm."
            else:
                c, reason = "biological_data_reader", "Native source acquisition/reader wrapper; not an additional independent biological algorithm."
            r.update(classification=c, scope_reason=reason, in_algorithm_or_data_reader_scope=not c.startswith("excluded"), registered_in_gentner_query_tools=name in registered)
            if basename == "online_queries" and not c.startswith("excluded"):
                r["underlying_callable"] = "gentner_ave.tools.ncbi.query_ncbi_database" if name in {"query_geo", "query_clinvar", "query_dbsnp"} else "biomni.tool.database." + name
                r["output_contract_note"] = "JSON serialized to a string and cut at 10,000 characters; truncated text is not lossless native data. Structured input bypasses optional Biomni prompt-to-query LLM path."
            if name == "inspect_file":
                r["supported_input_formats"] = ["Parquet", "CSV", "TSV", "TXT", "AnnData H5AD", "JSON text preview", "pickle object", "fallback byte/text preview"]
                r["output_contract_note"] = "Bounded shape/schema/preview text; does not preserve complete scientific results."
            if name == "download_geo_series":
                r["supported_input_formats"] = ["GEO series accession; GEOparse series SOFT acquisition"]
                r["output_contract_note"] = "Native GEOparse GSE; pivot VALUE -> expression CSV; phenotype metadata CSV; dictionary of paths, matrix dimensions, title, platform IDs, or structured error."
            gentner_entries.append(r)

    # Final classifications include Gentner reader and native-method overrides.
    # Resource semantics must use those final roles, never URL/class-closure heuristics.
    for r in entries + native_method_entries + gentner_entries:
        if r['implementation_present']:
            r['execution_routes'] = resource_routes(r)

    library = extract_literal(BIOMNI / "env_desc.py", "library_content_dict")
    additions = extract_literal(GENTNER / "src/gentner_ave/data/registry.py", "LIBRARY_ADDITIONS")
    datasets = extract_literal(GENTNER / "src/gentner_ave/data/registry.py", "TCGA_DATA_LAKE")
    upstream_datasets = extract_literal(BIOMNI / "env_desc.py", "data_lake_dict")
    commands = ["blastn", "blastp", "makeblastdb", "bwa", "samtools", "bcftools", "gatk", "snpEff", "lumpyexpress", "extractSplitReads_BwaMem", "cnvkit.py", "macs2", "findMotifsGenome.pl", "bedtools", "prokka", "pLannotate", "plannotate", "muscle", "clustalw", "clustalw2", "iqtree", "FastTree", "fasttree", "docker", "nvidia-smi", "prepare_receptor", "autosite", "conda", "Rscript", "state", "transcriptformer", "git"]
    counts = {
        "biomni_registered_entries": sum(x["registered_in_biomni_catalog"] for x in entries),
        "biomni_registered_modules": len(schema_names),
        "biomni_registered_missing_implementations": sum(x["registered_in_biomni_catalog"] and not x["implementation_present"] for x in entries),
        "biomni_unregistered_public_native_functions": sum(not x["registered_in_biomni_catalog"] for x in entries),
        "biomni_supporting_public_class_methods": len(native_method_entries),
        "biomni_catalog_classification": dict(collections.Counter(x["classification"] for x in entries if x["registered_in_biomni_catalog"])),
        "biomni_all_public_classification": dict(collections.Counter(x["classification"] for x in entries)),
        "gentner_query_tools_registered": sum(x.get("registered_in_gentner_query_tools", False) for x in gentner_entries),
        "gentner_query_tools_nonliterature": sum(x.get("registered_in_gentner_query_tools", False) and x["in_algorithm_or_data_reader_scope"] for x in gentner_entries),
        "gentner_owned_public_helpers": len(gentner_entries),
        "library_descriptions_only": len({**library, **additions}),
        "described_data_lake_entries_only": len({**upstream_datasets, **datasets}),
    }
    boundaries = [
        {"name": "native_result_capture", "sharing": "Shared immutable source-byte/object capture, parameters, versions, provenance and failure/partial-result typing. Keep each tool's native schema and actual branch distinct; remove neither data nor qualifications."},
        {"name": "blast", "members": ["blast_sequence"], "sharing": "Existing blast_graders parse native BLAST JSON/tabular; current Biomni XML first-HSP summary is lossy and cannot fill the existing sheet. Preserve full raw remote XML or change capture before reuse; no silent format equivalence."},
        {"name": "alignment_and_phylogeny", "members": ["analyze_protein_conservation", "analyze_protein_phylogeny", "align_sequences", "analyze_cas9_mutation_outcomes", "analyze_crispr_genome_editing", "find_sequence_mutations"], "sharing": "FASTA/alignment and actual residue-map readers may share; primer matching, pairwise edit classification, MSA conservation, distance trees and bootstrap/model statistics need separate semantics and calculators."},
        {"name": "sequence_features_and_design", "members": ["annotate_open_reading_frames", "annotate_plasmid", "annotate_bacterial_genome", "find_n_glycosylation_motifs", "predict_o_glycosylation_hotspots", "identify_transcription_factor_binding_sites", "identify_fas_functional_domains", "predict_protein_disorder_regions", "pcr_simple", "digest_sequence", "find_restriction_sites", "find_restriction_enzymes", "design_primer", "design_verification_primers", "design_golden_gate_oligos", "golden_gate_assembly", "optimize_codons_for_heterologous_expression"], "sharing": "Share explicit sequence coordinate/strand/interval primitives and native FASTA/GFF/GenBank readers where formats match. Motif occurrence, profile significance, ORF translation, disorder scores, predicted assembly and measured annotation support stay distinct."},
        {"name": "genomic_intervals_variants", "sharing": "BED, SAM/BAM, VCF and CNV tables permit shared native readers. MACS2 callpeak/bdgdiff, HOMER motif enrichment, LUMPY, Mutect2/snpEff, CNVkit and overlap/liftover each require method-specific numerical sheets; assembly/version/reference identities are mandatory."},
        {"name": "single_cell_embeddings", "sharing": "AnnData/H5AD readers and label-count arithmetic can share. scVI/scANVI, Harmony, UCE/IMA, PopV, panhumanpy, State, Transcriptformer and ESM are distinct models/output meanings. Embedding similarity is not calibrated function probability; retain weights/space/batch/labels and any stochastic settings."},
        {"name": "image_metrics", "sharing": "Share lossless image/mask/label and coordinate-unit readers. Keep segmentation, registration, optical flow, colocalization, intensity, counts and morphometry calculations explicit per tool. Presentation pixels and simulated fallbacks are not independent evidence."},
        {"name": "assay_time_series_models", "sharing": "Share arrays, units, replicate grouping, fit residual and parameter/covariance readers where identical. Michaelis-Menten, ITC, release, growth, cosinor, calcium, hemodynamic and ODE/stochastic models require separate parameter meanings, uncertainty and observed-versus-simulated status."},
        {"name": "chemical_structure_binding", "sharing": "Share SMILES/PDB/PDBQT/SDF native readers only where actually emitted. RDKit properties, Vina energies, DiffDock confidence, AutoSite pockets, DeepPurpose predictions and TxGNN rankings have different meanings and cannot share a category-derived grade."},
        {"name": "source_record_readers", "sharing": "Gentner structured wrappers and Biomni direct structured database calls can share a reader only for the same retained native schema and version. REST response envelopes and bounded prose are not scientific grading schemas. Local DDInter and remote FDA records remain distinct; no name-based cross-record joins."},
        {"name": "excluded_surfaces", "sharing": "Literature, generated prose/LLM, execution, discovery, presentation, robot instructions and mock experiments are accounted for, not counted as deterministic biological evidence. No Gentner agent roster, interpreter, retries, stopping or workflow is imported into the episode design."},
    ]
    result = {
        "inventory_version": "2026-10-24.2",
        "scope": "All 218 registered Biomni 0.0.8 catalog entries reachable through this Gentner checkout, all additional public native functions in those modules, supporting Gentner source readers, and explicit exclusions. Inventory only; no grader, prompt, execution or episode changes.",
        "provenance": {
            "requested_repository": "https://github.com/chrisagrams/gentner-ave",
            "local_checkout": str(GENTNER),
            "origin": "git@github.com:chrisagrams/gentner-ave.git",
            "local_HEAD": "892d70b4c887d95a9cb0898071cede656b344e67",
            "local_HEAD_date": "2026-08-03",
            "remote_HEAD_read_only_ls_remote": "892d70b4c887d95a9cb0898071cede656b344e67",
            "remote_verification_date": "2026-10-24",
            "public_web_result": "404 Not Found",
            "working_tree": "Previously modified and untracked files present. Inventory describes current local wrapper source; matching HEAD does not make local modifications upstream content. No checkout or source mutation was performed.",
            "dependency": "biomni==0.0.8 pinned by pyproject.toml; installed distribution metadata confirms version 0.0.8. Algorithms are dependency source, not Gentner-owned implementations.",
            "discovery_source": ref(BIOMNI / "utils.py", 845),
            "gentner_binding_source": ref(GENTNER / "src/gentner_ave/deps.py", 35),
            "dispatch_source": ref(GENTNER / "src/gentner_ave/execution/agent.py", 124),
            "local_biomni_module_hashes": {m: sha(fd["text"]) for m, fd in files.items()},
        },
        "counts": counts,
        "resource_route_correction": {
            "note": "Version 2 corrects the version-1 conflation of algorithm execution with network input/model acquisition. Tool scope, callable identities, classifications and inventory counts are unchanged.",
            "separate_fields": ["execution_routes.algorithm_execution", "execution_routes.input_acquisition", "execution_routes.model_and_software_acquisition", "execution_routes.generic_transport"],
            "no_network_placement_heuristic": True,
            "original_inventory_sha256": "8f6a570d401ae2c56b73660788ff7d32e0c29f99b7d3b1c2d3d6051d4ba1cc45",
            "reviewed_examples": ["split_modalities", "prepare_input_for_nnunet", "segment_with_nn_unet", "generate_gene_embeddings_with_ESM_models", "identify_transcription_factor_binding_sites", "analyze_fda_safety_signals", "blast_sequence", "predict_protein_disorder_regions", "identify_fas_functional_domains", "gene_set_enrichment_analysis", "analyze_ddr_network_in_cancer", "query_reactome"],
        },
        "inspection_limits": ["AST parsed every included catalog schema and every implementation in the 21 modules; extracted exact signatures, docstrings, all assignments, calls, outputs, command expressions and reachable helpers. Critical mock/fallback/resource paths received semantic review.", "No scientific algorithm, model, data service, script runner, container, installation, PBS/Slurm job or HPC launch was executed. Static metadata extraction and read-only git remote inspection are the only executed inventory operations.", "Per-tool source presence and filesystem package presence do not establish import success, compatible versions, scientific correctness, native executable availability outside PATH, database/model assets, service health or deployed HPC execution.", "This is not a completed line-by-line scientific validation of every algorithm; output grading still needs per-tool full-path review and native fixtures. Static unresolved-global findings identify source concerns without proving every conditional branch fails."],
        "resource_inventory": {
            "local": {"implemented": True, "source": ref(GENTNER / "src/gentner_ave/execution/backend.py", 101), "details": "Academy thread executor; Python imports and executes in the host interpreter. Scientific dependencies must exist there. R/bash helpers invoke configured Rscript/bash separately."},
            "api": {"implemented": True, "details": "Remote source acquisition and remote scientific computation are separate per-tool fields. BLAST/IUPred2A/HMMER have concrete remote analysis requests; Enrichr analysis is library-delegated and version/runtime-unverified. JASPAR/Ensembl/FDA data requests and Zenodo model downloads do not imply remote execution of their consuming algorithms. Gentner REST server is an investigation submission service, not another algorithm implementation."},
            "hpc": {"generic_transport_source": ref(GENTNER / "src/gentner_ave/execution/backend.py", 58), "details": "Globus Compute endpoint and Parsl transports exist. Optional extras, actual endpoint/provider configuration, authentication/exchange, environment, shared files and suitable resources required. Default Parsl LocalProvider does not establish HPC. No tool-specific PBS/Aurora adapter or deployment verified in Gentner.", "policy_for_future_aurora_runs": "Project storage /lus/flare/projects/BioReason-Aurora-Test; new PBS charging account EpiCalib. Inventory submitted no jobs."},
            "path_executable_presence_only": {x: shutil.which(x) for x in commands},
            "executable_check_note": "shutil.which inspects PATH/file presence only; no binary version or algorithm was run. Absence does not rule out other environments/HPC installations.",
        },
        "module_sharing_boundaries": boundaries,
        "biomni_entries": entries,
        "biomni_supporting_class_methods": native_method_entries,
        "gentner_owned_entries": gentner_entries,
        "library_menu_not_registered_algorithms": {**library, **additions},
        "data_lake_descriptions_not_availability": {**upstream_datasets, **datasets},
        "internal_helper_index": [{"module": "biomni.tool." + m, "name": n, **ref(fd["path"], f.lineno), "end_line": f.end_lineno} for m, fd in files.items() for n, f in fd["functions"].items() if n.startswith("_")],
    }
    (DEST / "gentner.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    report = ["# Gentner native tool inventory (2026-10-24)", "", "Inventory only; no scientific tools, installations, remote data requests or jobs were run.", "", "`reference/episode_tools` points to `git@github.com:chrisagrams/gentner-ave.git`. Read-only `git ls-remote origin HEAD` returned `892d70b4c887d95a9cb0898071cede656b344e67`, matching local HEAD; public GitHub returned 404. Existing local modifications remain, so current wrappers are distinguished from the committed snapshot. Scientific implementations are the installed, pinned **Biomni 0.0.8** dependency.", "", "## Counts", "", "```json", json.dumps(counts, indent=2), "```", "", "## Availability and retention", "", "Python/native implementations and API wrappers exist; their actual scientific execution was not tested. Per-entry imports, missing package candidates, native commands, model/data paths, source lines and exact outputs/calculations are in `gentner.json`. The local backend is an Academy thread; generic Globus/Parsl transports require deployment and authentication, and default Parsl uses LocalProvider. No tool-specific Aurora/HPC deployment was verified. A resource-menu or software description is not an executable algorithm or available dataset.", "", "Most algorithms return a prose log and write native sidecars. Gentner captures bounded stdout/`repr`, and direct query wrappers cut JSON text at 10,000 characters. Future graders must retain full native results and branch provenance. They need explicit numerical calculators with units and denominators; no source category can become an invented reliability number.", "", "## Material implementation qualifications", ""]
    for n in ["blast_sequence", "analyze_comparative_genomics_and_haplotypes", "analyze_protein_conservation", "analyze_cfse_cell_proliferation", "track_immune_cells_under_flow", "analyze_cns_lesion_histology", "detect_and_characterize_structural_variations", "quick_rigid_registration"]:
        report.append(f"- `{n}`: {' '.join(NOTES[n])}")
    report += ["", "Five mock-experiment tools and protocol/LLM/presentation helpers are explicitly excluded below. Genuine ODE/coalescent/stochastic simulations remain included as model outputs, separate from observations. Static unresolved-global and prerequisite findings are per entry; they are not runtime tests.", "", "## Resource classification correction", "", "Version 2 separates scientific calculation, input acquisition, model/software acquisition and generic transport. nnUNet segmentation computes in its worker after optional model download; modality preparation uses no model. ESM inference is local after Ensembl sequence acquisition and model loading. TFBS scans locally using retrieved JASPAR motifs; FDA signal arithmetic is local using retrieved reports. BLAST, IUPred2A and HMMER submit sequence calculations to remote services. Enrichr is delegated remote analysis with missing/unverified library versions. URL presence and broad class dependencies no longer determine computation placement; no HPC deployment is inferred from Globus/Parsl transport. Counts and work status are unchanged. See `gentner.resource_correction.md` for correction provenance.", "", "## Complete registered and native names", "", "Each name appears once below, grouped by source module and inventory class. These source groupings do not define grading equivalence or an episode itinerary.", ""]
    for module in sorted({e["module"] for e in entries}):
        group = [e for e in entries if e["module"] == module]
        report.append(f"### {module}")
        report.append("")
        for classification in sorted({e["classification"] for e in group}):
            names = ["`" + e["name"] + "`" + (" (native, unregistered)" if not e["registered_in_biomni_catalog"] else "") for e in group if e["classification"] == classification]
            report.append(f"- **{classification} ({len(names)})**: " + ", ".join(names) + ".")
        report.append("")
    report += ["## Supporting native class operations", "", "These operations expose underlying image/transform work and are not counted again as registered tools or independent evidence.", ""]
    for module in sorted({e['module'] for e in native_method_entries}):
        report.append(f"- `{module}`: " + ', '.join('`' + e['name'] + '` (' + e['classification'] + ')' for e in native_method_entries if e['module'] == module) + '.')
    report += ["", "## Gentner supporting readers and exclusions", ""]
    for module in sorted({e["module"] for e in gentner_entries}):
        group = [e for e in gentner_entries if e["module"] == module]
        report.append(f"- `{module}`: " + ", ".join("`" + e["name"] + "` (" + e["classification"] + ")" for e in group) + ".")
    report += ["", "## Boundaries for independent grading work", ""]
    for b in boundaries:
        report.append(f"- **{b['name']}**: {b['sharing']}")
    report += ["", "Do not import Gentner's agent roster, interpretation helper, retries, stopping behavior or workflow into this episode implementation. A common reader is appropriate only for actual shared native format/meaning; each independent method retains its own sheet components and calculators.", "", "Rebuild the static inventory with `python3 research/tool_grader_inventory_2026-10-24/gentner.inventory.py`. The JSON retains every catalog schema, callable signature, full implementation docstring, source hash/line, direct and same-module helper calls, assignments/calculations, native write/command expressions, package-presence findings and exclusions. Source extraction is comprehensive; scientific validation of all method paths remains future work."]
    (DEST / "gentner.md").write_text("\n".join(report) + "\n")
    print(json.dumps(counts, indent=2))
    print("Outputs:", DEST / "gentner.json", DEST / "gentner.md")


if __name__ == "__main__":
    main()
