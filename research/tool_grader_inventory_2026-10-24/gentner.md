# Gentner native tool inventory (2026-10-24)

Inventory only; no scientific tools, installations, remote data requests or jobs were run.

`reference/episode_tools` points to `git@github.com:chrisagrams/gentner-ave.git`. Read-only `git ls-remote origin HEAD` returned `892d70b4c887d95a9cb0898071cede656b344e67`, matching local HEAD; public GitHub returned 404. Existing local modifications remain, so current wrappers are distinguished from the committed snapshot. Scientific implementations are the installed, pinned **Biomni 0.0.8** dependency.

## Counts

```json
{
  "biomni_registered_entries": 218,
  "biomni_registered_modules": 21,
  "biomni_registered_missing_implementations": 1,
  "biomni_unregistered_public_native_functions": 4,
  "biomni_supporting_public_class_methods": 17,
  "biomni_catalog_classification": {
    "scientific_algorithm": 122,
    "excluded_mock_experiment": 5,
    "scientific_model_simulation": 13,
    "biological_data_preparation": 3,
    "excluded_presentation": 1,
    "excluded_missing": 1,
    "biological_data_reader": 53,
    "excluded_llm": 2,
    "excluded_discovery": 2,
    "excluded_lab_automation": 3,
    "excluded_literature": 8,
    "excluded_protocol": 4,
    "excluded_execution": 1
  },
  "biomni_all_public_classification": {
    "scientific_algorithm": 122,
    "excluded_mock_experiment": 5,
    "scientific_model_simulation": 13,
    "biological_data_preparation": 4,
    "excluded_presentation": 3,
    "excluded_missing": 1,
    "biological_data_reader": 54,
    "excluded_llm": 2,
    "excluded_discovery": 2,
    "excluded_lab_automation": 3,
    "excluded_literature": 8,
    "excluded_protocol": 4,
    "excluded_execution": 1
  },
  "gentner_query_tools_registered": 24,
  "gentner_query_tools_nonliterature": 20,
  "gentner_owned_public_helpers": 41,
  "library_descriptions_only": 114,
  "described_data_lake_entries_only": 97
}
```

## Availability and retention

Python/native implementations and API wrappers exist; their actual scientific execution was not tested. Per-entry imports, missing package candidates, native commands, model/data paths, source lines and exact outputs/calculations are in `gentner.json`. The local backend is an Academy thread; generic Globus/Parsl transports require deployment and authentication, and default Parsl uses LocalProvider. No tool-specific Aurora/HPC deployment was verified. A resource-menu or software description is not an executable algorithm or available dataset.

Most algorithms return a prose log and write native sidecars. Gentner captures bounded stdout/`repr`, and direct query wrappers cut JSON text at 10,000 characters. Future graders must retain full native results and branch provenance. They need explicit numerical calculators with units and denominators; no source category can become an invented reliability number.

## Material implementation qualifications

- `blast_sequence`: NCBIWWW.qblast remote XML path only, fixed expect=100, word_size=7, megablast=True; returns the first HSP of the first hit, discarding other HSPs/hits and the raw XML. Reported coverage is len(hsp.query)/len(input sequence)*100, which counts alignment-string characters rather than gap-resolved paired residues. Existing blast_graders need retained native results, not this lossy summary.
- `analyze_comparative_genomics_and_haplotypes`: Partially implemented: BWA alignment can be real, but BWA-success variants are a placeholder string; fallback compares at most ten base differences by same record ID. Haplotype groups use sample index modulo 3, with random variant counts and divergence times. These haplotype numbers are not scientific results.
- `analyze_protein_conservation`: MUSCLE failure triggers right-padding input sequences to equal length, then constructs an identity-distance NJ tree; this fallback is not an MSA. Conservation includes gaps in the most-common-character fraction and writes values rounded to two decimals.
- `analyze_cfse_cell_proliferation`: Real FCS branch exists; missing FlowCytometryTools generates mock populations, while read/gating errors substitute division_index=1.2 and percent_proliferating=65.0. Both synthetic branches must be marked non-observational.
- `track_immune_cells_under_flow`: Image-loading and tracking failures can substitute dummy images and simulated tracks; retain branch provenance before scoring trajectory metrics.
- `analyze_cns_lesion_histology`: Missing scikit-image or image-processing failure substitutes stain-specific simulated metrics; retain branch provenance and do not grade them as image measurements.
- `detect_and_characterize_structural_variations`: LUMPY calling is implemented, but requested COSMIC/ClinVar annotation step is explicitly simulated. The split-read shell pipeline is passed as a list with shell=True and needs execution repair/verification.
- `quick_rigid_registration`: Default create_visualizations=True references a missing ImageRegistrationTool.create_registration_visualization method; scientific registration and metric outputs must be isolated/verified.

Five mock-experiment tools and protocol/LLM/presentation helpers are explicitly excluded below. Genuine ODE/coalescent/stochastic simulations remain included as model outputs, separate from observations. Static unresolved-global and prerequisite findings are per entry; they are not runtime tests.

## Resource classification correction

Version 2 separates scientific calculation, input acquisition, model/software acquisition and generic transport. nnUNet segmentation computes in its worker after optional model download; modality preparation uses no model. ESM inference is local after Ensembl sequence acquisition and model loading. TFBS scans locally using retrieved JASPAR motifs; FDA signal arithmetic is local using retrieved reports. BLAST, IUPred2A and HMMER submit sequence calculations to remote services. Enrichr is delegated remote analysis with missing/unverified library versions. URL presence and broad class dependencies no longer determine computation placement; no HPC deployment is inferred from Globus/Parsl transport. Counts and work status are unchanged. See `gentner.resource_correction.md` for correction provenance.

## Complete registered and native names

Each name appears once below, grouped by source module and inventory class. These source groupings do not define grading equivalence or an episode itinerary.

### biomni.tool.biochemistry

- **excluded_mock_experiment (1)**: `analyze_enzyme_kinetics_assay`.
- **scientific_algorithm (5)**: `analyze_circular_dichroism_spectra`, `analyze_rna_secondary_structure_features`, `analyze_protease_kinetics`, `analyze_itc_binding_thermodynamics`, `analyze_protein_conservation`.

### biomni.tool.bioengineering

- **excluded_mock_experiment (1)**: `perform_crispr_cas9_genome_editing`.
- **scientific_algorithm (5)**: `analyze_cell_migration_metrics`, `analyze_calcium_imaging_data`, `analyze_in_vitro_drug_release_kinetics`, `analyze_myofiber_morphology`, `decode_behavior_from_neural_trajectories`.
- **scientific_model_simulation (1)**: `simulate_whole_cell_ode_model`.

### biomni.tool.bioimaging

- **biological_data_preparation (3)**: `split_modalities`, `prepare_input_for_nnunet`, `preprocess_image` (native, unregistered).
- **excluded_missing (1)**: `create_registration_visualization`.
- **excluded_presentation (1)**: `create_segmentation_visualization`.
- **scientific_algorithm (6)**: `segment_with_nn_unet`, `quick_rigid_registration`, `quick_affine_registration`, `quick_deformable_registration`, `batch_register_images`, `calculate_similarity_metrics`.

### biomni.tool.biophysics

- **scientific_algorithm (3)**: `predict_protein_disorder_regions`, `analyze_cell_morphology_and_cytoskeleton`, `analyze_tissue_deformation_flow`.

### biomni.tool.cancer_biology

- **scientific_algorithm (6)**: `analyze_ddr_network_in_cancer`, `analyze_cell_senescence_and_apoptosis`, `detect_and_annotate_somatic_mutations`, `detect_and_characterize_structural_variations`, `perform_gene_expression_nmf_analysis`, `analyze_copy_number_purity_ploidy_and_focal_events`.

### biomni.tool.cell_biology

- **scientific_algorithm (5)**: `quantify_cell_cycle_phases_from_microscopy`, `quantify_and_cluster_cell_motility`, `perform_facs_cell_sorting`, `analyze_flow_cytometry_immunophenotyping`, `analyze_mitochondrial_morphology_and_potential`.

### biomni.tool.database

- **biological_data_reader (40)**: `query_uniprot`, `query_alphafold`, `query_interpro`, `query_pdb`, `query_pdb_identifiers`, `query_kegg`, `query_stringdb`, `query_iucn`, `query_paleobiology`, `query_jaspar`, `query_worms`, `query_cbioportal`, `query_clinvar`, `query_geo`, `query_dbsnp`, `query_ucsc`, `query_ensembl`, `query_opentarget`, `query_monarch`, `query_openfda`, `query_gwas_catalog`, `query_gnomad`, `query_reactome`, `query_regulomedb`, `query_pride`, `query_gtopdb`, `query_remap`, `query_mpd`, `query_emdb`, `query_synapse`, `query_pubchem`, `query_chembl`, `query_unichem`, `query_clinicaltrials`, `query_dailymed`, `query_quickgo`, `query_encode`, `region_to_ccre_screen`, `get_genes_near_ccre`, `get_hpo_names` (native, unregistered).
- **scientific_algorithm (1)**: `blast_sequence`.

### biomni.tool.genetics

- **scientific_algorithm (7)**: `liftover_coordinates`, `bayesian_finemapping_with_deep_vi`, `analyze_cas9_mutation_outcomes`, `analyze_crispr_genome_editing`, `identify_transcription_factor_binding_sites`, `fit_genomic_prediction_model`, `analyze_protein_phylogeny`.
- **scientific_model_simulation (2)**: `simulate_demographic_history`, `perform_pcr_and_gel_electrophoresis`.

### biomni.tool.genomics

- **biological_data_reader (3)**: `get_rna_seq_archs4`, `get_gene_set_enrichment_analysis_supported_database_list`, `interspecies_gene_conversion`.
- **excluded_llm (1)**: `annotate_celltype_scRNA`.
- **scientific_algorithm (15)**: `annotate_celltype_with_panhumanpy`, `create_scvi_embeddings_scRNA`, `create_harmony_embeddings_scRNA`, `get_uce_embeddings_scRNA`, `map_to_ima_interpret_scRNA`, `gene_set_enrichment_analysis`, `analyze_chromatin_interactions`, `analyze_comparative_genomics_and_haplotypes`, `perform_chipseq_peak_calling_with_macs2`, `find_enriched_motifs_with_homer`, `analyze_genomic_region_overlap`, `unsupervised_celltype_transfer_between_scRNA_datasets`, `generate_embeddings_with_state`, `generate_gene_embeddings_with_ESM_models`, `generate_transcriptformer_embeddings`.

### biomni.tool.glycoengineering

- **excluded_discovery (1)**: `list_glycoengineering_resources`.
- **scientific_algorithm (2)**: `find_n_glycosylation_motifs`, `predict_o_glycosylation_hotspots`.

### biomni.tool.immunology

- **excluded_mock_experiment (1)**: `isolate_purify_immune_cells`.
- **scientific_algorithm (9)**: `analyze_atac_seq_differential_accessibility`, `analyze_bacterial_growth_curve`, `estimate_cell_cycle_phase_durations`, `track_immune_cells_under_flow`, `analyze_cfse_cell_proliferation`, `analyze_cytokine_production_in_cd4_tcells`, `analyze_ebv_antibody_titers`, `analyze_cns_lesion_histology`, `analyze_immunohistochemistry_image`.

### biomni.tool.lab_automation

- **excluded_lab_automation (3)**: `test_pylabrobot_script`, `get_pylabrobot_documentation_liquid`, `get_pylabrobot_documentation_material`.

### biomni.tool.literature

- **excluded_literature (8)**: `fetch_supplementary_info_from_doi`, `query_arxiv`, `query_scholar`, `query_pubmed`, `search_google`, `extract_url_content`, `extract_pdf_content`, `advanced_web_search_claude`.

### biomni.tool.microbiology

- **excluded_mock_experiment (1)**: `enumerate_bacterial_cfu_by_serial_dilution`.
- **scientific_algorithm (7)**: `analyze_arsenic_speciation_hplc_icpms`, `count_bacterial_colonies`, `annotate_bacterial_genome`, `quantify_biofilm_biomass_crystal_violet`, `segment_and_analyze_microbial_cells`, `segment_cells_with_deep_learning`, `predict_rna_secondary_structure`.
- **scientific_model_simulation (4)**: `optimize_anaerobic_digestion_process`, `model_bacterial_growth_dynamics`, `simulate_generalized_lotka_volterra_dynamics`, `simulate_microbial_population_dynamics`.

### biomni.tool.molecular_biology

- **biological_data_reader (3)**: `get_gene_coding_sequence`, `get_plasmid_sequence`, `design_knockout_sgrna`.
- **excluded_protocol (3)**: `get_oligo_annealing_protocol`, `get_golden_gate_assembly_protocol`, `get_bacterial_transformation_protocol`.
- **scientific_algorithm (12)**: `annotate_open_reading_frames`, `annotate_plasmid`, `align_sequences`, `pcr_simple`, `digest_sequence`, `find_restriction_sites`, `find_restriction_enzymes`, `find_sequence_mutations`, `design_primer`, `design_verification_primers`, `design_golden_gate_oligos`, `golden_gate_assembly`.

### biomni.tool.pathology

- **scientific_algorithm (7)**: `analyze_aortic_diameter_and_geometry`, `analyze_atp_luminescence_assay`, `analyze_thrombus_histology`, `analyze_intracellular_calcium_with_rhod2`, `quantify_corneal_nerve_fibers`, `segment_and_quantify_cells_in_multiplexed_images`, `analyze_bone_microct_morphometry`.

### biomni.tool.pharmacology

- **biological_data_reader (7)**: `query_drug_interactions`, `check_drug_combination_safety`, `analyze_interaction_mechanisms`, `find_alternative_drugs_ddinter`, `query_fda_adverse_events`, `get_fda_drug_label_info`, `check_fda_drug_recalls`.
- **excluded_mock_experiment (1)**: `analyze_accelerated_stability_of_pharmaceutical_formulations`.
- **excluded_protocol (1)**: `run_3d_chondrogenic_aggregate_assay`.
- **scientific_algorithm (14)**: `run_diffdock_with_smiles`, `docking_autodock_vina`, `run_autosite`, `retrieve_topk_repurposing_drugs_from_disease_txgnn`, `predict_admet_properties`, `predict_binding_affinity_protein_1d_sequence`, `grade_adverse_events_using_vcog_ctcae`, `analyze_radiolabeled_antibody_biodistribution`, `estimate_alpha_particle_radiotherapy_dosimetry`, `perform_mwas_cyp2c19_metabolizer_status`, `calculate_physicochemical_properties`, `analyze_xenograft_tumor_growth_inhibition`, `analyze_western_blot`, `analyze_fda_safety_signals`.

### biomni.tool.physiology

- **scientific_algorithm (10)**: `reconstruct_3d_face_from_mri`, `analyze_abr_waveform_p1_metrics`, `analyze_ciliary_beat_frequency`, `analyze_protein_colocalization`, `perform_cosinor_analysis`, `calculate_brain_adc_map`, `analyze_endolysosomal_calcium_dynamics`, `analyze_fatty_acid_composition_by_gc`, `analyze_hemodynamic_data`, `quantify_amyloid_beta_plaques`.
- **scientific_model_simulation (1)**: `simulate_thyroid_hormone_pharmacokinetics`.

### biomni.tool.support_tools

- **biological_data_reader (1)**: `download_synapse_data`.
- **excluded_discovery (1)**: `read_function_source_code`.
- **excluded_execution (1)**: `run_python_repl`.
- **excluded_presentation (2)**: `clear_captured_plots` (native, unregistered), `get_captured_plots` (native, unregistered).

### biomni.tool.synthetic_biology

- **biological_data_preparation (1)**: `create_biochemical_network_sbml_model`.
- **scientific_algorithm (6)**: `engineer_bacterial_genome_for_therapeutic_delivery`, `analyze_bacterial_growth_rate`, `analyze_barcode_sequencing_data`, `analyze_bifurcation_diagram`, `optimize_codons_for_heterologous_expression`, `identify_fas_functional_domains`.
- **scientific_model_simulation (1)**: `simulate_gene_circuit_with_growth_feedback`.

### biomni.tool.systems_biology

- **excluded_llm (1)**: `query_chatnt`.
- **scientific_algorithm (2)**: `perform_flux_balance_analysis`, `compare_protein_structures`.
- **scientific_model_simulation (4)**: `model_protein_dimerization_network`, `simulate_metabolic_network_perturbation`, `simulate_protein_signaling_network`, `simulate_renin_angiotensin_system_dynamics`.

## Supporting native class operations

These operations expose underlying image/transform work and are not counted again as registered tools or independent evidence.

- `biomni.tool.bioimaging.ImageRegistrationTool`: `load_image` (biological_data_reader), `save_image` (biological_data_preparation), `preprocess_image` (biological_data_preparation), `create_rigid_transform` (biological_data_preparation), `create_affine_transform` (biological_data_preparation), `create_deformable_transform` (biological_data_preparation), `setup_registration_method` (excluded_configuration), `register_images` (scientific_algorithm), `calculate_similarity_metrics` (scientific_algorithm).
- `biomni.tool.bioimaging.SegmentationTool`: `split_modalities` (biological_data_preparation), `prepare_input_for_nnunet` (biological_data_preparation), `setup_nnunet_environment` (excluded_configuration), `segment_with_nn_unet` (scientific_algorithm), `create_segmentation_visualization` (excluded_presentation).
- `biomni.tool.pharmacology.OpenFDAClient`: `query_adverse_events` (biological_data_reader), `query_drug_labels` (biological_data_reader), `query_drug_recalls` (biological_data_reader).

## Gentner supporting readers and exclusions

- `gentner_ave.tools.biomni_catalog`: `get_tool_schema` (excluded_execution_or_discovery), `list_module_tools` (excluded_execution_or_discovery), `search_libraries` (excluded_execution_or_discovery).
- `gentner_ave.tools.data_lake`: `data_lake_one_liners` (excluded_execution_or_discovery), `download_geo_series` (biological_data_reader), `inspect_file` (biological_data_reader).
- `gentner_ave.tools.execution`: `run_bash_script` (excluded_execution_or_discovery), `run_python_subprocess` (excluded_execution_or_discovery), `run_r_code` (excluded_execution_or_discovery).
- `gentner_ave.tools.literature`: `query_arxiv` (excluded_literature), `query_pubmed` (excluded_literature), `query_scholar` (excluded_literature), `search_google` (excluded_literature).
- `gentner_ave.tools.ncbi`: `efetch` (biological_data_reader), `esearch` (biological_data_reader), `esummary` (biological_data_reader), `query_ncbi_database` (biological_data_reader).
- `gentner_ave.tools.online_queries`: `query_alphafold` (biological_data_reader), `query_arxiv` (excluded_literature), `query_cbioportal` (biological_data_reader), `query_chembl` (biological_data_reader), `query_clinicaltrials` (biological_data_reader), `query_clinvar` (biological_data_reader), `query_dailymed` (biological_data_reader), `query_dbsnp` (biological_data_reader), `query_encode` (biological_data_reader), `query_ensembl` (biological_data_reader), `query_geo` (biological_data_reader), `query_gnomad` (biological_data_reader), `query_gwas_catalog` (biological_data_reader), `query_interpro` (biological_data_reader), `query_kegg` (biological_data_reader), `query_opentarget` (biological_data_reader), `query_pdb` (biological_data_reader), `query_pubchem` (biological_data_reader), `query_pubmed` (excluded_literature), `query_reactome` (biological_data_reader), `query_scholar` (excluded_literature), `query_stringdb` (biological_data_reader), `query_uniprot` (biological_data_reader), `search_google` (excluded_literature).

## Boundaries for independent grading work

- **native_result_capture**: Shared immutable source-byte/object capture, parameters, versions, provenance and failure/partial-result typing. Keep each tool's native schema and actual branch distinct; remove neither data nor qualifications.
- **blast**: Existing blast_graders parse native BLAST JSON/tabular; current Biomni XML first-HSP summary is lossy and cannot fill the existing sheet. Preserve full raw remote XML or change capture before reuse; no silent format equivalence.
- **alignment_and_phylogeny**: FASTA/alignment and actual residue-map readers may share; primer matching, pairwise edit classification, MSA conservation, distance trees and bootstrap/model statistics need separate semantics and calculators.
- **sequence_features_and_design**: Share explicit sequence coordinate/strand/interval primitives and native FASTA/GFF/GenBank readers where formats match. Motif occurrence, profile significance, ORF translation, disorder scores, predicted assembly and measured annotation support stay distinct.
- **genomic_intervals_variants**: BED, SAM/BAM, VCF and CNV tables permit shared native readers. MACS2 callpeak/bdgdiff, HOMER motif enrichment, LUMPY, Mutect2/snpEff, CNVkit and overlap/liftover each require method-specific numerical sheets; assembly/version/reference identities are mandatory.
- **single_cell_embeddings**: AnnData/H5AD readers and label-count arithmetic can share. scVI/scANVI, Harmony, UCE/IMA, PopV, panhumanpy, State, Transcriptformer and ESM are distinct models/output meanings. Embedding similarity is not calibrated function probability; retain weights/space/batch/labels and any stochastic settings.
- **image_metrics**: Share lossless image/mask/label and coordinate-unit readers. Keep segmentation, registration, optical flow, colocalization, intensity, counts and morphometry calculations explicit per tool. Presentation pixels and simulated fallbacks are not independent evidence.
- **assay_time_series_models**: Share arrays, units, replicate grouping, fit residual and parameter/covariance readers where identical. Michaelis-Menten, ITC, release, growth, cosinor, calcium, hemodynamic and ODE/stochastic models require separate parameter meanings, uncertainty and observed-versus-simulated status.
- **chemical_structure_binding**: Share SMILES/PDB/PDBQT/SDF native readers only where actually emitted. RDKit properties, Vina energies, DiffDock confidence, AutoSite pockets, DeepPurpose predictions and TxGNN rankings have different meanings and cannot share a category-derived grade.
- **source_record_readers**: Gentner structured wrappers and Biomni direct structured database calls can share a reader only for the same retained native schema and version. REST response envelopes and bounded prose are not scientific grading schemas. Local DDInter and remote FDA records remain distinct; no name-based cross-record joins.
- **excluded_surfaces**: Literature, generated prose/LLM, execution, discovery, presentation, robot instructions and mock experiments are accounted for, not counted as deterministic biological evidence. No Gentner agent roster, interpreter, retries, stopping or workflow is imported into the episode design.

Do not import Gentner's agent roster, interpretation helper, retries, stopping behavior or workflow into this episode implementation. A common reader is appropriate only for actual shared native format/meaning; each independent method retains its own sheet components and calculators.

Rebuild the static inventory with `python3 research/tool_grader_inventory_2026-10-24/gentner.inventory.py`. The JSON retains every catalog schema, callable signature, full implementation docstring, source hash/line, direct and same-module helper calls, assignments/calculations, native write/command expressions, package-presence findings and exclusions. Source extraction is comprehensive; scientific validation of all method paths remains future work.
