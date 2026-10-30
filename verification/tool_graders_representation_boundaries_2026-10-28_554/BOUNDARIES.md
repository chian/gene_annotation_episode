# Representation operation boundaries — source review 554

This is a proposed implementation boundary, awaiting root's exact-port freeze. It records source facts and necessary seams for the nine assigned R3 names. It is not a goal amendment, a working implementation, a verification of native calculations, or a completion claim. No production files, fixed progress rows, prompts, or resource configuration were changed. No application/scientific package was imported; no test, native job, installation, model download, or dataset acquisition was run.

The original attachment is authoritative; its path and full SHA256 are in SOURCE_MANIFEST.json. Existing repository designs and inventory rows are evidence. All nine relevant fixed rows currently have pending tool_info, sheet_contract, readers, calculators, result_path_binding and verification; their exact snapshot is in INSPECTION.json. Their source presence does not justify changing those columns.

## Numerical ownership and existing reuse

The exact-name search of production Python in gene_annotation_episode and method_loop returned no matches for any of the nine names. Searches for embedding/celltype/cosine/neighbor and matrix-label comparison owners found no existing production representation grader. The installed Biomni module and its descriptor catalog are a source catalog, not an episode binding. Its top-level imports also require esm, gget, gseapy, scanpy, torch, pybiomart and biomni.llm even for individual operations that do not use all of them; source presence does not establish that the module can be imported. None of these nine function bodies invokes an LLM. A future finite producer should bind the actual required native operation, not inherit an unrelated LLM workflow or every module-wide dependency.

Existing expression_nmf_common, expression_nmf_sheet, expression_nmf_calculations and their result consumers were read. Their sheet is a distinct nonnegative factorization analysis: gene-by-sample X, W[G,K], H[K,S], reconstruction residuals and component contributions. These wrappers do not emit W/H, and signed latent coordinates are not nonnegative expression factors. Reuse NMF's existing result-custody/worker/return architecture as an integration example; do not send embeddings into the NMF sheet or duplicate its reconstruction calculations. The pure complete-dense shape/finite predicate expression_nmf_common.matrix_valid(matrix, rows, columns, nonnegative=False), together with finite(), is reusable as written for complete finite decoded arrays. Its acceptance does not establish model-space or entity compatibility. No representation-specific norm, pooling or label calculator was found. numerical.py is the yield-estimator family, not a representation scoring authority.

PROPOSED one shared sheet: molecular_representation_sheet_v1, owned by molecular_representation_sheet.py with types in molecular_representation_contracts.py. It contains common representation arrays and entity axes, plus declared components for labels, native neighbor evidence and explicit pooling. No wrapper gets a copy of this sheet. The components are distinct quantities, not a master confidence or a new inference algorithm.

PROPOSED common numerical owners:

| Component | Sole proposed owner | Applies to |
| --- | --- | --- |
| Matrix shape/population, finite-element diagnostics, row L2 norm, coordinate mean/population variance, explicitly selected same-space Euclidean/cosine comparisons | representation_matrix_calculations.py | Every genuine decoded representation matrix; each model space remains separately identified |
| Counts/fractions of categorical assignments and explicit same-population label agreement; native-neighbor label counts, tie set, mean distance and exact legacy distance transform | representation_label_calculations.py | panhumanpy, IMA, popV; any other wrapper only when it actually supplies labels/neighbor operands |
| Explicit arithmetic pooling with retained child-to-parent membership and denominators | representation_pooling_calculations.py | ESM residue-to-isoform and isoform-to-gene means; other models only when their native pooling and operands are established |
| Saved-sheet validation and selected numerical projection | molecular_representation_sheet.py and representation_result_views.py | All nine, calling the same numerical owners |

SCVI and SCANVI are two different fitted model spaces, even in the same file. Harmony, UCE, State, Transcriptformer and ESM spaces are not interchangeable. Equal dimension, matching model family names, similar gene lists, or common cell labels do not establish coordinate correspondence. Independently trained SCVI models require separate fitted-model identities. A pretrained space needs exact weights/configuration/layer, feature/token vocabulary and preprocessing identities. Unknown identity permits retention and within-artifact descriptive measurements, but cannot establish cross-artifact coordinate compatibility. No alignment of independently fitted latent spaces is invented here.

## Exact operation mapping and source behavior

All source spans below refer to reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py. Complete bodies and hashes are retained in SOURCE_FUNCTIONS.md and SOURCE_MANIFEST.json. Dimensions use N query cells, M reference cells, G input feature occurrences, D representation coordinates, K selected neighbors, L protein residues and I retained isoforms. D is discovered from actual output and model metadata; no default D is assumed.

### annotate_celltype_with_panhumanpy (600–795)

Actual signature: `(adata_path, feature_names_col=None, refine=True, umap=True, output_dir='./output') -> str research_log`.

Real calls: constructs panhumanpy.AzimuthNN from an H5AD input; reads `azimuth.cells_meta`; optionally calls azimuth_embed, azimuth_umap and azimuth_refine; then packs an annotated object. This is reference-model hierarchical cell-label inference and optional representation generation, not a deterministic gene-function annotation rule. The panhumanpy model implementation/weights/atlas are not present in the inspected environment, so their exact preprocessing and label-score semantics remain unknown.

Input is AnnData X[N,G], obs cell occurrences and var feature occurrences. Feature identifiers come from a selected var column or var index. Intended native outputs are annotated_cell_metadata.csv (N metadata rows), ann_embeddings.npy (N,D), ann_umap.npy (normally a coordinate array, exact native dimensions unobserved), and annotated_obj.h5ad. Common sheet components: representation matrices and categorical labels with hierarchy/atlas identity; native scalar score fields only with their actual declared meaning. Preserve original and refined labels separately when both are available. No probability of gene-function correctness.

Dependencies: Conda, a named panhumanpy_env, an unpinned git installation of satijalab/panhumanpy, its model/reference assets, scanpy/pandas/numpy and input H5AD. Source automatically creates the environment and installs on missing env; this is acquisition/environment work that must become explicit episode-selected preparation. Package availability is unverified outside the inspected directory.

Specific source defects and missing seams:

- `azimuth.azimuth_umap()` return is discarded. The local `umap` remains the boolean argument; np.save(ann_umap.npy, umap) therefore writes a scalar boolean, not UMAP coordinates. Never admit this as an N-by-D representation. The packed H5AD may contain proper UMAP coordinates, but that is not established by this wrapper source.
- Embedding/UMAP exceptions exit zero before saving previously produced cell metadata. Preserve valid label results before optional downstream failure.
- Missing feature_names_col silently falls back to index; selected feature identity must remain explicit and the mismatch must be returned for episode repair.
- Partial errors and save failures are reduced to prose logs; output_dir may be overwritten and temporary evidence is removed. Capture native output roles, actual row joins, result extent and located failures instead.

Required binding output: retained metadata CSV plus exact ordered cell-to-input map, full available arrays, annotated H5AD, actual model/atlas IDs, selected/refined label columns and their taxonomy levels, and explicit partial statuses. Reader must reject scalar ann_umap.npy while retaining other valid outputs.

### create_scvi_embeddings_scRNA (801–839)

Actual signature: `(adata_filename, batch_key, label_key, data_dir) -> str steps`.

Real calls: SCVI.setup_anndata(adata, batch_key=batch_key); creates/trains SCVI; obtains `X_scVI`; creates SCANVI.from_scvi_model with labels_key and unlabeled_category='Unknown'; trains SCANVI and obtains `X_scANVI`. It trains two related models, not only scVI. It does not call a classifier prediction function.

Input: H5AD X[N,G], obs[batch_key] and obs[label_key]. No count layer or preprocessing is supplied to setup_anndata: the original X scale and count provenance are therefore important. Output: scvi_emb_data.h5ad retaining original data plus obsm X_scVI[N,D1] and X_scANVI[N,D2]. D1/D2, model configurations, seeds and realized training parameters are unobserved. Units are model-specific latent coordinates, not counts/TPM. Both arrays use the original cell occurrence axis, subject to validation against native output.

Necessary numerical owner: common matrix component for each distinct model space. Model diagnostics may be retained as native fields if actually captured; no reconstruction metric or latent uncertainty is inferred from these two arrays. Inherited input labels must not be relabeled as new predictions.

Dependencies: scvi-tools plus training stack, scanpy, numerical dependencies and supplied raw/count-qualified data. SCVI/SCANVI training uses package defaults without pinning or saved realized configuration. Source retains neither fitted model nor training history/checkpoints; output is only H5AD and log. A SCANVI failure can lose already completed SCVI work because the file is written only after both succeed. The child-owned producer must retain each completed model result, feature/batch/label setup, exact model identity and partial state. Fixed output filename has no request-identity safeguard.

### create_harmony_embeddings_scRNA (842–857)

Actual signature: `(adata_filename, batch_key, data_dir) -> str steps`.

Real call: `from harmony import harmonize` (source comment names harmony-pytorch), then `harmonize(adata.obsm['X_pca'], adata.obs, batch_key=batch_key)`. It applies Harmony batch integration to an existing PCA representation; it does not compute PCA or fit an expression reconstruction model.

Input: H5AD with X_pca[N,Dp], exact PCA model/loadings/preprocessing identity where available and obs[batch_key]. Output: harmony_emb_data.h5ad with obsm X_harmony, expected N-by-Dp but actual shape must be checked. Preserve original X_pca, batch assignments and new fitted integration/model identity. Native signed coordinates are arbitrary representation units; no explained variance or gene-function support is implied.

Necessary owner: common matrix component. Comparing corrected and original coordinates requires an explicit native transformation relation; shared shape alone is insufficient. Source saves no Harmony diagnostics, realized settings or model provenance and assumes the PCA field exists. The harmony implementation and default details are not installed in the inspected directory. Missing PCA, batch column or invalid output are typed input/native failures. Native library training/convergence behavior remains an external dependency, not a new calculator.

### get_uce_embeddings_scRNA (861–911)

Actual signature: `(adata_filename, data_dir, DATA_ROOT='/dfs/project/bioagentos/data/singlecell/', custom_args=None) -> str steps`.

Real calls: imports `eval_single_anndata.main, parse_args_uce`; parses custom arguments with appended `--adata_path` and `--dir`; constructs accelerate.Accelerator; invokes UCE main. There is no IMA mapping call despite the descriptor claiming generation and reference mapping together.

Input: selected H5AD and exact UCE model/species/feature vocabulary/checkpoint arguments once established. Claimed output path is `<data_dir>/<first-basename-token>_uce_adata.h5ad`, while execution receives output directory `<data_dir>/uce/`. Actual UCE output path/layout and D are unknown because eval_single_anndata is unavailable. IMA's consumer requires obsm['X_uce'][N,D]; this wrapper's log incorrectly says obs['X_uce']. Native data must decide the actual slot, never the log.

Necessary owner: common matrix component; no labels or atlas scores inferred. Retain source ordered cells/features, UCE model/layer/token/protein-embedding identities, species and preprocessing; explicit exclusion map if UCE filters features/cells.

Specific defects: import happens before sys.path is extended with DATA_ROOT/UCE; an external code directory alone cannot satisfy that import. Existing claimed output path causes a blind skip without checking input/model identity or native content. custom_args is mutated in place and may already contain conflicting CLI flags. Accelerate/model weights/external script are unbound; no native artifacts are validated by this wrapper. Do not adopt the unrelated absolute DATA_ROOT as a configured local/HPC resource. Result discovery and identity validation must be supplied by a real version-pinned producer.

### map_to_ima_interpret_scRNA (914–971)

Actual signature: `(adata_filename, data_dir, custom_args=None) -> str steps`.

Real algorithm: sklearn.neighbors.NearestNeighbors fits reference IMA.X[M,D]; kneighbors(query.obsm['X_uce'][N,D]) returns distances[N,K] and reference row indices[N,K]. It gathers reference obs['coarse_cell_type_yanay'], applies majority vote when K>1, and writes query obs mapped_cell_type and mapping_confidence. Tie handling uses np.unique sorting followed by first argmax, so the native winning label is the first sorted tied label, not an uncertainty-resolved answer. Defaults intended by source: K=3, metric='euclidean'.

Reference is hard-coded relative to data_dir as uce_10000_per_dataset_33l_8ep_coarse_ct.h5ad. That filename is not evidence of exact atlas version, training weights or shared coordinate space. Source checks only D equality. Output is adata_with_mapped_celltypes.h5ad. Native neighbors, distances and label votes are discarded.

Native `mapping_confidence = 1/(1 + mean(distances, axis=1))`. Retain this exact native reported field separately, named as reported with explicit semantics: an uncalibrated inverse distance transform. It is neither a calibrated label probability nor gene-function confidence. Distances have the selected metric's units in the exact shared UCE space; the transform's numerical scaling is specific to that space. Root explicitly required this separation.

Necessary owner: shared matrix compatibility component plus shared native-neighbor/label component. Required retained operands: complete query/reference matrices or stable retained references to both, ordered query/reference occurrences, native distances and native reference indices, exact selected K/metric and fitted neighbor parameters, full reference labels and their source/ontology identity. Calculate summaries of those operands once; displays consume calculated fields and preserve native conflicts. Do not regenerate KNN as a hidden parser/calculator step.

Defects: default custom_args=None raises at `.get`; source does not verify weight/model/preprocessing compatibility, K<=M, neighbor validity or label completeness; references are implicit in data_dir; no native neighbor table survives for saved recalculation. Preserve complete/partial and unknown-version states. Missing space identity is not fixed by finding D equality.

### unsupervised_celltype_transfer_between_scRNA_datasets (18–105)

Actual signature: `(path_to_annotated_h5ad, path_to_not_annotated_h5ad, ref_labels_key, query_batch_key=None, ref_batch_key=None, CELLTYPIST=False, KNN_BBKNN=False, KNN_HARMONY=False, KNN_SCANORAMA=False, KNN_SCVI=False, ONCLASS=False, Random_Forest=False, SCANVI_POPV=True, Support_Vector=False, XGboost=False, n_jobs=1, output_folder='./tmp/', n_samples_per_label=10) -> str steps`.

Real calls: popv.preprocessing.Process_Query(query, reference, ref_labels_key, batch keys, save_path_trained_models, cl_obo_folder=False, prediction_mode='retrain').adata; popv.annotation.annotate_data with the exact enabled method list. This is reference-trained label transfer. The wrapper name 'unsupervised' does not change use of annotated reference labels. SCANVI_POPV is enabled by default, and different method flags represent actual different upstream algorithms, not equivalent fitted models.

Inputs: reference expression X[M,Gr], query X[N,Gq], explicit reference labels[M], batch metadata and feature identifiers. Wrapper copies both X values into layers['counts'] without checking whether they are counts. No counts provenance is created by that copy. It delegates feature matching, preprocessing, training and prediction to popV. Their exact implementation/defaults/output schema remain unobserved because popV is unavailable. Native expected file path is `<output_folder>/popv_output/predictions.csv`; trained model output location is passed to Process_Query. No combined AnnData is saved explicitly by the wrapper, and no CSV columns are verified.

Necessary owner: common label-assignment component with separate method/model IDs and optional common matrix components only for actual retained embeddings. All ten flags remain distinct modes. Native class probabilities, votes or score margins need their actual per-method definitions and class-axis maps; none may be replaced by agreement with another model. If native consensus is emitted, retain its exact contributing method set and native agreement denominator. Reference population is not a query validation truth set.

Specific defects: n_samples_per_label is never used; log always says SCANVI_POPV regardless of selected methods; no-method selection still invokes annotate_data; normalized X can be mislabeled counts; feature mappings, query/reference occurrence partitions and per-method outputs are unretained or implicit. Native reference/query IDs must remain namespaced, including duplicate cell barcodes; no label joins by independently sorted rows. Source flags alone do not prove installed methods or usable OnClass ontology resources.

### generate_embeddings_with_state (2167–2419)

Actual signature: `(adata_filename, data_dir, model_folder, output_filename=None, checkpoint=None, embed_key='X_state', protein_embeddings=None, batch_size=500) -> str log`.

Real operation: external `uv run state emb transform --model-folder ... --input ... --output ...` with optional checkpoint, embed-key, protein-embeddings and batch-size. The wrapper claims SE-600M. The actual state/arc-state CLI implementation, selected checkpoint/configuration, output array slot and D have not been observed. Native output path is `<data_dir>/output/<input-stem>_state_embeddings.h5ad` unless specified. Preserve H5AD and verified cell/feature map; only a genuine numeric representation[N,D] can enter the common matrix component.

Dependencies: input H5AD; scanpy and torch; git-lfs; uv; the state CLI; SE-600M model/config/protein embedding resources. Source clones arcinstitute/SE-600M from Hugging Face when the folder is absent or none of four existence indicators is found; a config.yaml alone counts as model_exists. Source text estimates about 25 GB model files and 10+ GB GPU memory. These are upstream claims, not measured resource use. A roughly 25 GB default model acquisition is incompatible with the caller's 4 GiB local scratch boundary and cannot be silently initiated here. Actual resource-specific deployment remains unknown, and no HPC/CPU substitute is selected by this mapping.

Defects: doc/descriptor claims installs of git-lfs/uv/arc-state, but code only checks git-lfs and invokes uv; no such install steps are implemented. GPU availability determines warning/CPU fallback behavior, not a validated selected allocation. The wrapper retries a failing subprocess up to four attempts while halving batch_size, without preserving separate selected attempts. Strip this decision from a finite producer; return the specific failure and partial artifacts to the responsible episode. The CSR and gene_name checks merely warn (the indices attribute alone also does not uniquely establish CSR). The log calls X_state a 'layer' without inspecting native output. Output existence and complete row associations are never checked. No checkpoint or protein feature vocabulary digest is retained.

### generate_transcriptformer_embeddings (2422–2759)

Actual signature: `(adata_filename, data_dir, output_filename=None, model_type='tf-sapiens', checkpoint_path=None, batch_size=8, precision='16-mixed', clip_counts=30, embedding_layer_index=-1, num_gpus=1, n_data_workers=0, gene_col_name='ensembl_id', pretrained_embedding=None, filter_to_vocabs=True, use_raw='None', emb_type='cell', remove_duplicate_genes=False, oom_dataloader=False) -> str output_path`.

Real operation: optionally `transcriptformer download model_type`, followed by local preparation and `transcriptformer inference` on a temporary H5AD. It exposes tf-sapiens/tf-exemplar/tf-metazoa model choices and 'cell'/'cge' output modes. Native architecture, vocabulary, model resource identity, shapes and output storage locations are unknown until the real CLI implementation/output is available. Cell mode is intended N-by-D mean-pooled representation per source description; contextual-gene mode must preserve cell-by-feature/token-by-coordinate relationships, potentially ragged. Do not force CGE into a global gene-by-D matrix or invent a pooling method.

Inputs: expression H5AD X[N,G], possible raw matrix, gene identifiers and assay metadata; selected model/checkpoint/protein embedding files; exact clipping/vocabulary/filter/raw/precision/device parameters. Output path defaults to `<data_dir>/output/<input-stem>_transcriptformer_embeddings.h5ad`. Necessary owner: common matrix component for true cell matrices, and explicit contextual entity rows `(cell occurrence, gene/token occurrence, coordinate)` for CGE. Any pooling component is available only after native pooling semantics and complete membership are captured.

Defects: embedding_layer_index is never used or passed to CLI. gene_col_name is passed to inference but preparation hardcodes ensembl_id and validates var.index patterns first, so valid selected metadata columns can be rejected. download does not receive custom checkpoint_path; the subsequent existence assertion is not verified against returned acquisition. If raw is absent, current adata is assigned as raw even when X is normalized; raw counts remain unestablished. remove_duplicate_genes strips accession versions and keeps first feature, deleting others without an aggregation/membership record. 'assay=unknown' is an explicit missing value and must remain so. Prepared input is removed after success, losing the exact preprocessing record. Output existence/format and layer request compliance are not verified. CLI defaults and actual model version are not pinned.

### generate_gene_embeddings_with_ESM_models (314–460; helper 284–311)

Actual signature: `(ensembl_gene_ids: list[str], model_name='esm2_t6_8M_UR50D', layer=6, save_path=None, batch_size=1, max_sequence_length=1024) -> str steps`.

Real algorithm: `esm.pretrained.load_model_and_alphabet(model_name)`; Ensembl REST protein isoform fetch per gene; filter whole sequences longer than max_sequence_length (not truncate); tokenize; obtain native model representations at selected layer; mean each isoform's residue representations excluding BOS/EOS; take an unweighted arithmetic mean of retained successful isoform vectors for each gene. Native `.pt` artifact is only `{gene_id: tensor[D]}`. It is a protein-language-model representation, not an asserted gene-function annotation.

Required native relationships: requested gene occurrence -> provider gene/version -> transcript/protein/isoform accession/version -> sequence bytes and length -> token/residue positions and mask -> model/layer -> isoform vector -> gene mean with exact retained membership. Token tensor native B-by-T-by-D includes special/padding positions; scientific residue arrays use L-by-D with explicit token-to-residue mapping. Isoform vector is D; gene vector D. No D is assumed from the default model name.

Dependencies: Ensembl sequence acquisition (existing molecular-provider binding should be reused when available), fair-esm/torch, model weights and tokenizer/config, numerical libraries and selected CPU/GPU resource. _fetch_isoform_sequences calls live requests.get without a timeout, discards FASTA headers and returns [] on both response failure and no usable FASTA. Its docstring claims a special ENSP exclusion, but implementation contains no such filtering. Preserve implementation truth; do not implement the obsolete special case from the docstring.

Defects: native protein/isoform IDs are discarded, synthetic `_isoform_i` numbering is introduced after filtering, failed/long/missing isoforms disappear, duplicate requested gene IDs collapse in the dict, and saved means omit both isoform vectors and residue operands. Default save path is CWD-based; GPU is selected opportunistically; OOM causes unselected single-item retries. There is no model-weight digest, provider release, population completeness or typed partial result. The string-label split is not an accession join. The producer must preserve native identities, full native arrays (or explicitly declared native unavailability), excluded/failed populations, exact pooling membership and partial outcomes. Pure calculators must not fetch sequences or load/run ESM.

Necessary owners: common matrix plus explicit pooling components; same common numeric projection as other wrappers. A legacy mean-only artifact permits retention and bounded vector inspection, but cannot support recalculation of residue/isoform pooling or claim complete isoform coverage. Saving a gene mean does not repair lost metadata.

## Proposed shared data and function ports

These are proposed signatures and fields, not installed functions. Root must freeze them before coding assignments. A concrete dependency such as the native panhuman label schema, UCE output layout, State output key or Transcriptformer CGE representation still needs authentic source/output evidence; a parser must return unsupported_native_format for an unestablished layout instead of guessing.

All table keys below are internal typed keys, not scientific scores or model-facing tracking. Native text labels use restricted strings with their source identity. Complete artifacts remain retained; projection windows never change denominators.

### Input and native records

- `Artifact`: reuse NativeFileIdentity `{artifact_ref, sha256, size_bytes, format}`; format/version must be checked by an actual parser. Separate selected request, original attempt and writer-closure/capture identities belong to the existing execution infrastructure.
- `EntityOccurrence`: `{entity_key, dataset_key, axis, position, native_label, source_artifact, native_locator, supplied_identity}`. `axis` is cell, feature, residue, token, isoform, gene, or contextual_gene. `position` is zero-based native occurrence, not a public identifier. `supplied_identity` retains species/taxon, gene/transcript/protein/isoform accession and version, sample/condition/replicate and reference role when actually supplied. Missing meanings are null with a qualification. Duplicate native labels stay distinct. A contextual_gene requires both cell and feature/token occurrence keys.
- `ModelSpace`: `{space_key, algorithm, role, software_versions, weights_identity, fitted_model_identity, model_config_identity, model_identifier, model_revision, layer, coordinate_count, feature_axis_identity, vocabulary_identity, tokenizer_identity, preprocessing_identity, precision, reference_dataset_identity, uncertainty_source}`. Roles distinguish fitted_model, pretrained_model, corrected_pca and visualization. Unobserved identities remain null; a boolean field or filename is never sufficient proof. Model-space compatibility is an explicit result with reasons, never inferred from shape alone.
- `MatrixInput`: retained native array locator, actual dtype/order/sparse encoding, shape `(N,D)`, exact ordered row keys, ordered coordinate positions `0..D-1`, ModelSpace, numeric unit (`model_specific_latent_coordinate` or actual supplied native unit), and extent complete/partial/unavailable/incompatible. A sparse X expression matrix is not automatically a sparse embedding matrix; exact selected slot is required. Each decoded number is finite or has an explicit missing/nonfinite/failed cell status. Native bytes preserve NaN/Inf bit patterns; JSON null is not measured zero. Missing rows are declared, never zero padded.
- `LabelsInput`: one row per entity, method/model, hierarchy level and label schema; fields `{entity_key, method_key, space_key?, label_value?, label_state, hierarchy_level?, ontology_identity?, reference_dataset_identity?, native_score_fields[]}`. `label_state` distinguishes assigned, unassigned, unavailable, failed and incompatible. Native score fields retain name, value, meaning, range/units and class-axis/conditioning population where known. Unknown score meaning blocks a probability interpretation.
- `NeighborsInput`: `{query_entity_key, reference_dataset_key, space_key, requested_k, metric, neighbor_rows[]}` with each native neighbor `{rank, reference_row_position, reference_entity_key, distance, label_value, label_schema_key}`. Store selected/reference population, exact K, metric parameters, sorted/tie behavior, any search approximation, source ndarray locators, and native reported mapped label/legacy score. Missing distance/index/label fields stay missing; partial K does not silently use a smaller denominator as complete.
- `PoolingInput`: `{pool_key, parent_entity_key, input_representation_key, output_representation_key, method='arithmetic_mean', members[]}` where members identify child occurrence, exact included coordinates/residues, inclusion/exclusion/failure state and weight. ESM native mode has unit weights for each residue within each isoform and unit weights for each successfully included isoform within each gene. Requested, eligible, excluded, failed and completed member sets are separate. No automatic accession collapse or length weighting.
- `NativeDiagnostic`: actual native name/value/units/population/model/meaning and source locator; diagnostics are observed model output, not recomputed quality scores. No fabricated loss, variance explained, calibration, uncertainty, count-scale or training convergence.
- `Failure`: `{code, stage, artifact_ref?, native_locator?, entity_key?, representation_key?, field?, required_input?, partial_artifact_refs[]}`. Codes include unsupported_native_format/version, dependency_unbound, model_identity_unknown, model_space_incompatible, reference_conflict, axis_join_missing/ambiguous, native_shape_mismatch, native_value_nonfinite, native_output_missing/partial, invalid_parameter, input_scale_unknown, original_attempt_mismatch, artifact_digest_mismatch, missing_pool_membership, zero_denominator, zero_vector, numeric_overflow and native_value_conflict. No unbounded prose findings or fabricated confidence are needed.

### Reader, sheet and calculator ports

```text
read_h5ad_representation(retained: ArtifactBinding,
    selection: H5adArraySelection, entities: EntityBindings,
    model: ModelSpace) -> ParsedMatrix
read_numeric_array(retained: ArtifactBinding,
    selection: NpyOrTensorSelection, entities: EntityBindings,
    model: ModelSpace) -> ParsedMatrix
read_label_table(retained: ArtifactBinding,
    selection: CsvOrH5adLabelSelection,
    entities: EntityBindings, labels: LabelSchemaBindings) -> ParsedLabels
read_neighbor_arrays(distances: ParsedMatrix, indices: ParsedIndexMatrix,
    query_entities: EntityAxis, reference_entities: EntityAxis,
    reference_labels: ParsedLabels, specification: NeighborSpecification)
    -> ParsedNeighbors
populate_representation_sheet(*, original_request: RepresentationRequest,
    parsed_matrices: list[ParsedMatrix], parsed_labels: list[ParsedLabels],
    parsed_neighbors: list[ParsedNeighbors], pooling: list[PoolingInput],
    native_diagnostics: list[NativeDiagnostic]) -> RepresentationSheet
validate_representation_sheet(sheet: RepresentationSheet) -> RepresentationSheet
calculate_matrix_components(sheet: RepresentationSheet,
    selection: MatrixCalculationSelection) -> MatrixComponents
calculate_label_components(sheet: RepresentationSheet,
    selection: LabelCalculationSelection) -> LabelComponents
calculate_pooling_components(sheet: RepresentationSheet,
    selection: PoolingCalculationSelection) -> PoolingComponents
project_representation_result(sheet: RepresentationSheet,
    components: RepresentationComponents,
    selector: RepresentationResultSelector) -> RepresentationProjection
```

`ArtifactBinding` supplies only an already retained file and verified local read path inside the bounded worker; acquisition/capture remains elsewhere. Readers may decode actual H5AD/NPY/PT native formats only inside the declared runtime. Pure sheet population and calculations consume supplied decoded data and explicit selections: no file acquisition, subprocess, model inference, training, neighbor search, retry or LLM. Format readers share contracts and arithmetic. H5AD versions and torch tensor formats are declared and pinned, not inferred from suffix. The native torch decoder must restrict supported tensor content; it is not permission to execute arbitrary deserialization payloads.

Every `RepresentationSheet` holds immutable original request/parameters, artifact identities, entity axes, ModelSpaces, parsed matrices/labels/neighbors/pooling/diagnostics, native outcomes, qualifications and failures. Calculated components are separate, tied to sheet and explicit calculation-selection identities. Store full matrices/labels/neighbor rows and pooling operands, in retained array artifacts when not appropriate inline. Numerical changes require new calculated results and never rewrite prior sheet/native observations.

`RepresentationResultSelector` chooses component/view, explicit representation/model/entity/label schema IDs, fields, and row window `{offset, limit}`. Proposed views: matrix_summary, matrix_rows, selected_pair_measurements, assignments, label_summary, neighbor_rows, neighbor_summary, pooling_components and native_diagnostics. Return `{view, fields, rows, total_available_rows, selected_population_count, returned_row_count, row_offset, has_more, units, denominators, extent, qualifications, failures}`. The bounded row window applies after selecting the full declared population; it cannot silently shrink numerical denominators. Only the selected typed rows cross boundaries; saved-sheet identity is returned only if requested. Native annotations are controlled source labels, not unrestricted findings text.

### Exact numerical meanings

| Field/component | Definition and population | Unit / missing behavior |
| --- | --- | --- |
| declared rows, returned rows, dimensions, finite element count | Native axis lengths and count of actual finite values; declared element population is N*D | Counts. Missing shape/axis is failure; never infer rows from a log. Finite count is a data-availability diagnostic, not scientific confidence. |
| row L2 norm | sqrt(sum_j x[i,j]^2) over all D explicitly associated coordinates | Latent-coordinate units; use stable norm arithmetic. Any missing coordinate makes that row's full norm unavailable; zero is a valid norm. |
| coordinate mean/population variance | mean_j=sum_i x[i,j]/N; variance_j=sum_i (x[i,j]-mean_j)^2/N over an explicitly selected complete row population | Latent units / squared latent units. This is descriptive population variance, not explained variance or uncertainty. N=0 or incomplete population gives unavailable plus reason. |
| selected same-space Euclidean distance | sqrt(sum_j (x[j]-y[j])^2) using explicit coordinate and entity joins | Latent units; reject incompatible/unknown cross-artifact spaces, missing coordinates and overflow. Within one retained matrix is allowed. |
| selected same-space cosine | sum_j x[j]y[j] / (norm(x)*norm(y)) | Dimensionless similarity, not probability. Zero vector -> unavailable/zero_vector. Unknown space -> incompatible/unknown, never compare equal-sized unrelated embeddings. |
| label count and fraction | count for each exact label within the selected method/hierarchy/reference schema; assigned denominator and total requested denominator are separately named | Count and fraction [0,1]. Unassigned/missing/failed counts separate. No hidden removal from the denominator. Same text under different label schemas is not equality. |
| optional label agreement | Matches/comparable paired entities where explicit keys join two compatible label schemas; exact contingency counts retained | Fraction; denominator is explicit comparable population, with separate requested population and missing-pair counts. Not accuracy unless an independent supplied truth set is declared; never treat model/reference training labels as held-out truth. |
| native neighbor mean distance | Sum of all K actual returned native distances / K for the declared complete neighbor set | Native metric units; requested K and observed K separate. Missing/truncated neighbors do not produce a complete-set mean. No new search is performed. |
| native neighbor votes/ties | Counts of the K retained native reference labels; fraction uses K; tie set and native chosen label retained | Count and vote fraction; no calibration. Preserve source np.unique tie policy only for the actual IMA operation/version. |
| inverse-one-plus-mean neighbor distance | 1/(1+native-neighbor-mean-distance), explicitly mirroring IMA source, alongside its native reported mapping_confidence | Uncalibrated model/metric-specific transform; not a posterior and not gene-function support. Preserve native-minus-calculated conflict. Undefined if required distance set is incomplete/invalid. |
| ESM isoform residue mean | z_iso[j] = sum over retained biological residue positions r of T_iso[r,j] / L_iso, excluding declared BOS/EOS/padding | Latent units. Empty sequence or missing residue map -> unavailable. Retain L and token/residue membership. |
| ESM gene mean | z_gene[j] = sum over exactly I included completed isoforms of z_iso[j] / I | Latent units. I is successful included-isoform population, with requested/eligible/failed/excluded counts separately retained. I=0 unavailable, not zero vector. No residue-length weighting is substituted. |
| native-vs-calculated discrepancy | Native value minus matching component computed from complete retained operands with explicit comparison tolerance in the selection | Same native units; retain both values and qualification. Projection must not recompute or choose a more convenient value silently. |

Native uncertainty remains unknown unless a real native posterior/interval and its population are supplied. Model-family claims are not uncertainty measurements. No new batch-mixing score, biological conservation score, gene relevance ranking, classifier training, or coordinate-alignment algorithm is introduced by these calculations.

## Actual ownership path and missing integration seams

The present wrapper path is Biomni descriptor -> direct Python wrapper -> scientific library/CLI -> local output or string path/log. None of the nine names is currently found in production episode tool configuration, result selection or requested return handlers. An ordinary Python call is not a child-owned result path.

The existing production pattern inspected in full includes ScientificToolLibrary resolution, tool_information workflow declarations; ExecutionEpisodes.resource_tool_contracts/catalog/execute; native NMF tool contracts, result capture/worker/projector, and ExpressionNMFReturns. This is source-level path evidence, not a claim of running the NMF path or verifying all of the episode runtime. Existing full NMF numerical semantics must remain unchanged.

Required seams, with concrete consumers:

1. **Selected real tool information.** Add actual representation operation contracts only for configured resource software/model bindings. Existing ScientificToolLibrary.resolve_tool_info/resolve_invocations and ExecutionEpisodes.resource_tool_contracts consume them. Need name, substantive description/instructions, input schema and commission route. The unbound Biomni descriptor is insufficient. No new prompts were built here; later message work must use the task/steering instructions and user feedback.
2. **Correct resource child.** A selected request must contain exact native operation/mode, supplied input artifacts, model/reference/preprocessing operands, actual software identity and explicit allocation/output/cache directories. Launch retains resource choice where open; launch_local/launch_hpc retain their existing structures. ExecutionEpisodes.catalog/execute delegate to the chosen owner, not to a new private workflow. practical_execution_operations currently has explicit native_expression_nmf preparation/validation/handle/status/read hooks; none for these representations. Root owns integration edits in those shared dispatch files after reading the affected complete functions. This review indexed/searched those practical hooks but did not claim full practical-execution verification.
3. **Retained native outputs.** Reuse native_file_capture.capture_native_file/capture_declared_native_files and retained_native_file for custody. A finite producer supplies its output-role manifest, original request/attempt link, actual model/config/software versions, original and prepared inputs, row/feature maps, output arrays/labels/neighbors and located failures. It must not hide installation, dataset retrieval, selected-job substitution or retry decisions. Capture valid partial outputs before optional later stages fail.
4. **Reader -> common sheet -> one calculator per component.** A finite bounded result worker decodes actual formats, joins exact axes, validates model compatibility, populates one representation sheet and calls the shared numerical owners. NMF's expression_nmf_result_worker execute/validate/project separation is an example; its mode/schema/calculator cannot be copied as a representation score. Resource/format variants feed the same component functions. A saved-sheet worker uses retained operands only and can run with the original model and provider unavailable.
5. **Requested typed return.** Add representation fact sources for selected measurements, explicitly returned saved sheets and located failures. Native result publication and all displays must project retained calculated components. ExpressionNMFReturns._historical/_received/facts_for_closure/validate_received_report show the existing immediate-child and frozen-prefix custody behavior to preserve. Do not add another model call to restate arrays, labels or numerical facts. Parent interpretation remains limited to the declared return form.
6. **Consumer verification and continuation.** Test publication, result display, child form, receiving scientific parent and closed replay against the same saved components. Do not count native model stages, parsers or calculations as extra parent actions/observations. This mapping does not assign scientific credit or W05 aggregation, and no controller behavior changes are proposed.

## Independently ownable proposed files

Only this evidence directory is owned by this review. The following are proposed future assignments for root to freeze; nobody was delegated coding by this review.

| Future owner / files | Exact responsibility | Required input from another owner / returned output |
| --- | --- | --- |
| Shared contract owner: molecular_representation_contracts.py, molecular_representation_sheet.py | Entity/model/native/partial schemas, sheet population/validation and compatibility relationships; all nine names mapped to components | Frozen request types and actual native schema declarations -> one common sheet contract; no scientific inference |
| Matrix owner: representation_matrix_calculations.py | Common defined norm/mean/variance/same-space pair calculations only | Common sheet/selection -> MatrixComponents with exact units/denominators/qualifications; reuse existing finite/shape predicates for complete dense arrays |
| Label owner: representation_label_calculations.py | Assignment counts, explicitly requested compatible-label comparison, native-neighbor votes/mean distance/IMA transform | Common sheet, LabelSchemaBindings and native neighbors -> LabelComponents; no classifier/KNN execution |
| Pooling owner: representation_pooling_calculations.py | ESM's two explicit averaging levels and generic declared arithmetic-membership calculation | Complete retained residue/isoform matrices and exact pooling membership -> PoolingComponents; no sequence acquisition or model call |
| H5AD reader owner: representation_h5ad_reader.py | Selected numeric slots, row/feature maps, required original/prepared metadata; native HDF5 format/version handling | Verified retained artifacts + pinned decoder + exact selection -> ParsedMatrix/EntityAxis; authentic native layout is the specific dependency |
| Array reader owner: representation_array_reader.py | NPY numeric arrays and constrained tensor-map decoding, special-token/residue maps | Retained declared native arrays and explicit identity maps -> ParsedMatrix; reject bool scalar UMAP, incompatible shape or unbound serialization |
| Label reader owner: representation_label_reader.py | CSV/H5AD native label/score columns and native neighbor array relations | Actual versioned panhuman/popV/IMA schemas and explicit identity/label maps -> ParsedLabels/ParsedNeighbors; no interpretation from column-name resemblance |
| Producer owner: native_representation_driver.py plus native_representation_contracts.py | One selected native action on configured software/model resources, output manifest and native arrays/maps; preserves actual partial state | Frozen request + bound native implementation + actual selected inputs -> native bundle; no install/download/retry loop embedded in grader |
| Integration owner: native_representation_tool_info.py, native_representation_results.py, representation_result_worker.py, representation_result_views.py, representation_returns.py | Real resource commissioning, custody, bounded read/calculate/projection, requested return/replay | Frozen common contract, configured native producer, delivered readers/calculators -> typed measurements; reuse capture and existing episode lifecycle |
| Root shared dispatch owner | execution_episodes.py, practical_execution_operations.py, practical_execution_records.py and actual resource configuration/receiver registrations | Exact new ports delivered by the above -> selected-child path; no parser/calculator agent edits these files independently |

The pipeline can parallelize readers and calculators only after root freezes exact data types. Dependencies are specific: e.g. the label reader needs the native popV prediction table schema plus the query/reference occurrence map, not 'all single-cell work'; ESM pooling needs retained residue tensors and isoform membership, not a new provider implementation. Missing deployment blocks a native live test, not pure source-contract review or fixture cases for established numeric ports.

## Concrete future verification cases (not run)

All numerical examples here are deliberately constructed test specifications, not scientific measurements or tool executions.

1. Common matrix [[3,4],[0,0]] in one declared model space: N=2, D=2, finite count=4; row norms [5,0]; coordinate mean [1.5,2]; population variance [2.25,4]; first vector self-cosine=1; zero-vector cosine unavailable. Return precisely those retained components through a bounded row selector. Also test signed values, nonfinite native entries, empty and partial rows, numeric overflow and duplicate cell labels with distinct positions.
2. Two 2D matrices with different model weights, fitted IDs, layer, vocabulary or preprocessing: coordinate comparisons must not be emitted as compatible. In particular X_scVI and X_scANVI, two SCVI fits, and UCE vs State stay different despite same D. Unknown identity stays unknown. A within-one-artifact comparison remains available.
3. Label assignments A,B,A over three assigned cells out of four requested: A count=2, assigned-population fraction=2/3, B=1/3, assigned coverage=3/4 and one unassigned/missing state explicitly identified. Label schemas or hierarchy levels that differ cannot be merged by shared text.
4. Explicit same-entity comparison [A,B,None] versus independently supplied [A,C,C]: one match / two comparable rows=0.5; requested population=3; one incomparable pair. Do not label the statistic classifier accuracy without declared truth provenance. Test reordered rows, same barcode in reference/query, conflicting reference metadata and one-to-many joins.
5. IMA native neighbors distances [1,2,3] with labels [A,A,B]: mean distance=2, votes A=2 and B=1, winning-label fraction=2/3, exact legacy transform=1/3. A native reported value 0.4 is retained with a conflict against 1/3. A tie [B,A] records both tied labels and the native sorted-label winner A for this implementation. Test None custom_args, K>M, K=1, duplicated neighbors, missing labels/distances, incompatible UCE model, and partial K.
6. ESM two isoforms: residues [[1,3],[3,5]] -> [2,4]; residues [[6,8]] -> [6,8]; equal isoform mean -> [4,6]. A residue-weighted combined mean [10/3,16/3] is deliberately different and must not replace it. Exclude BOS/EOS/padding using the actual token map, preserve the denominator 2 isoforms and each residue count. Test one overlength isoform, one failed isoform, absent provider release, duplicate gene requests, empty sequences, wrong layer/D, legacy mean-only file and original FASTA header preservation.
7. panhumanpy: retain labels even when optional embedding/UMAP generation fails; reject the scalar bool ann_umap.npy; preserve unknown atlas/version and hierarchy; feature-column mismatch cannot silently fall back. Confirm the actual packed H5AD's fields separately.
8. scVI/SCANVI and Harmony: genuine tiny native runs in the root's frozen bounded runner after dependencies/resource fits are established; verify cells/features/batch/labels and signed arrays. Inject a SCANVI stage failure and retain prior SCVI output. Confirm original models/params and native history when available; no fabricated training metrics. Missing PCA or batch metadata is an actionable failure.
9. UCE: verify real external script version, import path, output path/slot and model vocabulary. A same-named existing file from another input/model is not accepted. Verify no IMA map is falsely claimed by the UCE operation.
10. State: exact prepared environment and checkpoint/protein vocabulary; actual selected native command and returned output array; failed command returns one actual attempt and partial artifacts, without automatic batch-size retries. Confirm actual model/resource footprint before any intended resource verification; do not download the source-claimed 25 GB model into local 4 GiB scratch.
11. Transcriptformer: actual cell and CGE native outputs tested separately. embedding_layer_index must actually reach supported inference configuration or return unsupported-parameter; preserve versioned feature identities and exact dropped/combined membership; custom gene_col_name works from declared metadata. Normalized X does not become measured raw counts. Download output/path, checkpoint selection, raw layer and assay unknown status remain explicit. Prepared input is retained, not deleted before capture.
12. Common integration: selected tool info -> correct resource child -> retained original attempt -> native reader -> shared sheet/components -> selected projection -> scientific-parent requested return. Assert identical numbers and native conflicts at every consumer; wrong request/attempt/artifact/axis rejected. Saved-only recalculation with model executables, provider network and original work directory absent; closed replay retains original facts and does not retrain, refetch, recalculate historical observations or create additional credit.

## Availability and reviewed completion

Verified by source/standard-library inspection: all nine wrapper bodies and catalog dictionaries exist; Biomni metadata says version 0.0.8. The inspected site-packages directory contains numpy 2.5.0, pandas 2.3.3 and requests 2.33.1 directory/metadata entries. This is presence evidence only, not import/runtime verification.

No corresponding top-level modules/distribution prefixes for esm, scanpy, scvi, popv, panhumanpy, harmony, eval_single_anndata, accelerate, transcriptformer, state or torch were present in that directory listing. This does not prove absence from every environment/Conda installation or resource. No remote API authentication, Conda env, GPU, UCE atlas/checkpoint, State/Transcriptformer model, Ensembl access, Aurora, Polaris or tailnet availability was probed. Those remain specifically unknown/unverified. No claim of actual installed/working representation operation is justified.

Reviewed mapping is complete for the nine assigned names and the explicitly listed production example consumers. Working tool information, exact deployed modes, authentic native-format readers, all common numerical components, result binding, numerical tests, saved replay, episode returns and live-resource verification remain unfinished for this representation group. SOURCE_MANIFEST.json distinguishes complete-file/function reads from search-only/index-only inspection. No broader episode-runtime review is claimed.
