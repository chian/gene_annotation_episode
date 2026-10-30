Source census: 2026-10-28

This is implementation evidence, not a goal or scope amendment. No production code/tests were changed or run.

| Analysis | Linked names | Exact public names |
| --- | ---: | --- |
| BLAST pairwise correspondence | 6 | bvbrc.homology.pairwise_correspondence, native.blastn, native.blastp, native.blastx, native.tblastn, native.tblastx |
| BLAST sequence database identification | 11 | api.blast.fetch, bvbrc.homology.database_identification, native.blastn, native.blastp, native.blastx, native.deltablast, native.psiblast, native.tblastn, native.tblastx, public.blast.collect, public.blast.search |
| BLAST profile database measurements | 3 | native.deltablast, native.rpsblast, native.rpstblastn |
| BLAST VDB correspondence and populations | 2 | native.blastn_vdb, native.tblastn_vdb |
| BLAST VDB candidate-function model | 2 | native.blastn_vdb, native.tblastn_vdb |
| HMMER protein search | 5 | api.hmmer.result, homology.extract, native.hmmscan, native.hmmsearch, native.jackhmmer |
| HMMER nucleotide search | 2 | native.nhmmer, native.nhmmscan |
| HMMER profile alignment | 1 | native.hmmalign |
| Infernal/Rfam search shared path | 3 | api.rfam.fetch, native.cmscan, native.cmsearch |
| Infernal covariance-model alignment | 1 | native.cmalign |
| RNA structure topology and energy | 2 | analyze_rna_secondary_structure_features, predict_rna_secondary_structure |
| RNA structure comparison | 0 |  |
| Protein structure comparison | 1 | compare_protein_structures |
| Genomic interval overlap | 1 | analyze_genomic_region_overlap |
| Chromatin contacts and insulation | 1 | analyze_chromatin_interactions |
| ATAC differential accessibility | 1 | analyze_atac_seq_differential_accessibility |
| Expression NMF | 1 | perform_gene_expression_nmf_analysis |
| Supplied fluorescence-event analysis | 2 | analyze_cytokine_production_in_cd4_tcells, perform_facs_cell_sorting |
| BV-BRC GeneTree phylogeny | 2 | bvbrc.gene_tree.concatenated_sequence_loci, bvbrc.gene_tree.gene_tree |
| BV-BRC CodonTree phylogeny | 1 | bvbrc.codon_tree.core_genome_codon_protein |
| BV-BRC multiple sequence alignment | 5 | bvbrc.msa.mauve_alignment, bvbrc.msa.ordinary_alignment, bvbrc.msa.prealigned_analysis, bvbrc.msa.segment_alignment, bvbrc.msa.segment_concatenation |
| BV-BRC MetaCATS | 3 | bvbrc.metacats.auto, bvbrc.metacats.files, bvbrc.metacats.groups |
| BV-BRC genome alignment | 1 | bvbrc.genome_alignment |
| BV-BRC proteome comparison | 1 | bvbrc.proteome_comparison |
| BV-BRC comparative systems | 1 | bvbrc.comparative_systems |
| BV-BRC read processing measurements | 1 | bvbrc.fastqutils |
| BV-BRC Similar Genome Finder / MinHash | 3 | api.bvbrc.minhash.fasta, api.bvbrc.minhash.genome, api.bvbrc.minhash.result |

Scope summary: {"analysis_rows": 27, "grader_name_links": 63, "unique_public_names": 55, "distribution": {"0": 1, "1": 12, "2": 6, "3": 4, "5": 2, "6": 1, "11": 1}, "public_names": "see census.json"}
Combined with eight parent-confirmed direct rows: {"analysis_rows": 35, "grader_name_links": 73, "unique_public_names": 65, "distribution": {"0": 1, "1": 18, "2": 8, "3": 4, "5": 2, "6": 1, "11": 1}, "public_names": "see census.json"}
Including two duplicate Rfam implementation paths: {"analysis_rows": 37, "grader_name_links": 75, "unique_public_names": 65, "distribution": {"0": 1, "1": 20, "2": 8, "3": 4, "5": 2, "6": 1, "11": 1}, "public_names": "see census.json"}

Source-level links do not establish completed live-resource or requested-return verification. Rfam duplicates, provider phylogeny sheet distinctions and RNA comparison generic binding are explicit in census.json.
