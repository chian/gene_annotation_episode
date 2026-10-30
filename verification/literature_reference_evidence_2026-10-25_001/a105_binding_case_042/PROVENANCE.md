# Source and research-work provenance042

Owner: fresh delegated binding research042. Scope: only this new directory. Selected retained metadata group/case_id reg_iscR_state_target_specificity, single primary PMC3676455, DOI10.1038/nsmb.2568. Selection was sent to root before primary acquisition/read. No new broad search, no companion paper and no retained actual_observations/starting_question read.

## Actual discovery and source coverage

The corpus/specificity/cases.jsonl was inspected only through whitelisted metadata fields case_id,gene_protein_organism,primary_source_urls,DOIs,verification_scope; no matching IscR record was found there. Actual case_records.json is a list of grouped wrappers. The matching group and nested record field names were inspected to locate its primary_source_urls and verification_scope. Neither nested starting_question nor actual_observations nor annotation_consequence values were displayed. Complete SOURCE_CORRECTIONS.md was read initially and again in the post-paper reset; SC01 concerns a different source/endpoint and is not imported into this case.

Primary URL https://pmc.ncbi.nlm.nih.gov/articles/PMC3676455/ was opened directly from its retained identifier. Web output displayed initial article lines0–262; a continuation attempt returned a recaptcha. A direct curl acquisition then supplied221580bytes of HTML. Python stdlib HTMLParser selected the article element, retained all its data text and rendered409nonblank text lines. All409lines were fully observed through sequential1–105,106–270,271–409 tool outputs without truncation. This includes full available Introduction, Results, Discussion, Online Methods, tables2/4, figure captions, references and supplement links. Main Table3 numeric cells are an image rather than text.

The Table3 image was acquired directly from the exact HTML img URL:
https://cdn.ncbi.nlm.nih.gov/pmc/blobs/8499/3676455/bb3549229f41/nihms-454929-t0001.jpg

It was visually inspected with view_image,600×221pixels. A later same-image display and pixel-row support check only located the retained transcription cell rectangles; no additional source paper or packet was opened. Numeric text was manually transcribed, not OCR. No values were digitized from response curves. Figure1–6 raster contents, their plotted points and supplemental plots were not visually inspected. Main-text statements/captions remain textual coverage, not plot verification.

Direct supplement URL https://pmc.ncbi.nlm.nih.gov/articles/instance/3676455/bin/NIHMS454929-supplement-1.pdf yielded HTML, not a PDF. The bytes are retained as failed_supplement_response.html; pdftotext failed. A direct same-identifier availability request to https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3676455/supplementaryFiles returned a ZIP containing only a zero-byte nihms-454929-f0002.gif. It did not supply the paper's supplement. No substitute paper or additional literature search was used. Supplementary curves, preparation details delegated to prior papers, raw traces and raw fitted-parameter covariance remain unverified/unavailable.

An exploratory rg file-name listing was excessively broad and tool-truncated; it displayed file names only and is not counted as a complete document read or authority acknowledgment. No truncated authority output was acknowledged. The initial unavailable `python` executable and absent bs4 dependency were handled with python3 stdlib; no environment installation was performed.

## Own required post-paper reset

read_authority.py is a new owner042 helper, using the older root helper only as a layout example. It does not import or reuse another worker's read acknowledgments. Its READ_RECEIPT.json records SHA256,byte/line counts and34sequential fully observed chunks. Each chunk was acknowledged only in a later tool invocation after its output was fully displayed; the helper recomputed all document identities at each invocation. All34were completed. The active literature goal appears first and last; latest039+040 immediately precede its final full read. No scientific interpretation was drafted until that completion.

The receipt covers the complete applicable authority set from research AGENTS, including original quotations and superseding corrections, full current696-line A105 numerical proposal, all seven existing binding modules and source experimental contracts. Historical target-transfer/source-pooling and candidate-contribution proposals were read for reset and are not adopted by this task. All raw authority bytes are identified by hashes in the receipt; the helper itself is hashed in FILE_MANIFEST.json.

Complete local binding paths read: literature_binding_reader.py193lines; calculations.py328; model_inputs.py136; models.py346; prompt.py25; storage.py250; model_storage.py248; literature_experimental_contracts.py156. Those are complete files, not matching snippets. No claim of fully tracing every inherited storage/runtime consumer is made here; integration audit041 owns that broader code audit and root review owns final conclusions. This packet limits executed capability claims to pure reader/calculator calls.

## Actual execution and boundaries

Executed with PYTHONPATH=. .venv/bin/python calculate_case.py: ten selected comparisons through read_binding_parameter_table,populate_binding_contrast,populate_binding_model(model=None), plus four direct research arithmetic calculations. Source-derived numerical cells are neither synthetic fixtures nor actual biological experiments. Existing production functions were imported and used without editing them. The assertions verify returned usable partials and unavailable profiles for these actual source operands, not broad adversarial coverage. No pytest, production episode, durable repository commission/return, live model, target annotation, tool-grader run or HPC work occurred. Application source strings in local records are research labels; none purports to be an admitted source reference in a scientific run.

All owned files are listed with size/SHA256 in FILE_MANIFEST.json. A105 and the active goal remain incomplete. Missing source scientific data and missing functions are distinguished in FINDINGS.md.
