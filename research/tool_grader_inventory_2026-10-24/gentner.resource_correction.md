# Resource classification correction — 2026-10-24

This correction updates inventory metadata to version `2026-10-24.2`. It does not change tool scope, identities, classifications, counts, or work status. No scientific tool, data acquisition, model download, installation or job was run.

The previous inventory conflated network activity with scientific algorithm execution. Broad class dependencies could also expose a download URL belonging to another method. Every implemented row now separates `algorithm_execution`, `input_acquisition`, `model_and_software_acquisition`, and `generic_transport`; URL presence never determines placement.

| Operation | Scientific calculation | Network purpose |
| --- | --- | --- |
| `split_modalities`, `prepare_input_for_nnunet` | Local NIfTI/file operations | None in these methods; no model is used |
| `segment_with_nn_unet` | Local worker inference using `predict_from_folder` | Optional acquisition of missing weights from Zenodo |
| `generate_gene_embeddings_with_ESM_models` | Local PyTorch inference and averaging | Ensembl sequence retrieval; delegated model-weight loading/download remains qualified |
| `identify_transcription_factor_binding_sites` | Local Biopython PSSM scan | JASPAR motif/PFM acquisition |
| `analyze_fda_safety_signals` | Local source-response calculations | OpenFDA report acquisition |
| `blast_sequence` | NCBI remote BLAST, followed by local parsing | Scientific calculation submission and result retrieval |
| `predict_protein_disorder_regions` | Remote IUPred2A prediction, followed by local grouping | Scientific calculation submission and result retrieval |
| `identify_fas_functional_domains` | Remote HMMER/Pfam scan, followed by local selection | Scientific calculation submission and result retrieval |
| `gene_set_enrichment_analysis`, enrichment stage of `analyze_ddr_network_in_cancer` | Enrichr analysis delegated through `gget`/`gseapy`; local preparation and summaries | Remote enrichment analysis; dependencies absent from inspected environments, exact deployed version/path unverified |

Enrichr's distinction is supported by current primary [gget source](https://raw.githubusercontent.com/pachterlab/gget/main/gget/gget_enrichr.py) and [GSEApy source](https://raw.githubusercontent.com/zqfang/GSEApy/master/gseapy/enrichr.py). These upstream files are not represented as installed or pinned dependencies. GSEApy also supports local enrichment branches; the inspected Gentner wrapper requests a named online library.

Generic database readers retain endpoint-dependent qualifications. In particular, Reactome's AnalysisService URL does not prove an implemented gene-list submission path: the inspected wrapper issues GET requests. Likewise, model/software downloads for DiffDock, DeepPurpose, panhumanpy, State and Transcriptformer do not imply remote inference. Generic Globus/Parsl transport remains separate from unverified tool-specific HPC deployment.

Counts remain **218 registered entries / 21 modules; 222 public top-level rows; 17 supporting class methods; 41 Gentner public helpers, including 24 query wrappers and 20 non-literature wrappers**. Algorithm/reader/exclusion counts are unchanged. Static checks verified the four separate resource fields on every implemented row, the reviewed placement cases, and `hpc_deployment_verified=false` throughout.

Previous SHA-256 values:

- `gentner.json`: `8f6a570d401ae2c56b73660788ff7d32e0c29f99b7d3b1c2d3d6051d4ba1cc45`
- `gentner.md`: `814af9dda445112563dd9a45ae75aeddce9727b7bcaf49169474d92688100f58`
- `gentner.inventory.py`: `1d27de868ea6d918b4db57a12e4ef3196e5473598ca10229eaac730a7711a0e2`

Corrected `gentner.json` SHA-256: `49f674f2bdb65ae0cfa2e5d41ef7d204d40880be10b102a261280b71af4ae853`.

Corrected `gentner.md` SHA-256: `7a145b5ac538412945deccb31d36e36ead9cb376bdbb2758d67521a6a43f421f`.

The regeneration script and this note have their own hashes reported to the parent for the master index. Only `gentner.*` inventory artifacts were changed.
