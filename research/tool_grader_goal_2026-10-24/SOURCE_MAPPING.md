# Complete source-to-requirement mapping

Historical observations remain evidence only. Matching a source entry does not prove native-format fidelity, deployment, invocation binding, numerical correctness or episode communication. A wrapper row and its provider row may share an implementation; this does not add an independent algorithm.

| Source ID | Source name | Required IDs | Source/disposition | Underlying callable |
| --- | --- | --- | --- | --- |
| SA-0001 | api.blast.fetch | A-L069-blastn-database, A-L069-blastp-database, A-L069-blastx-database, A-L069-tblastn-database, A-L069-tblastx-database, E-L287-ncbi-blast | entries/api.blast.fetch/api; mapped_required_or_scoped_helper | — |
| SA-0002 | api.blast.prepare | A-L069-blastn-database, A-L069-blastp-database, A-L069-blastx-database, A-L069-tblastn-database, A-L069-tblastx-database, E-L287-ncbi-blast | entries/api.blast.prepare/api; mapped_required_or_scoped_helper | — |
| SA-0003 | api.blast.status | A-L069-blastn-database, A-L069-blastp-database, A-L069-blastx-database, A-L069-tblastn-database, A-L069-tblastx-database, E-L287-ncbi-blast | entries/api.blast.status/api; mapped_required_or_scoped_helper | — |
| SA-0004 | api.blast.submit | A-L069-blastn-database, A-L069-blastp-database, A-L069-blastx-database, A-L069-tblastn-database, A-L069-tblastx-database, E-L287-ncbi-blast | entries/api.blast.submit/api; mapped_required_or_scoped_helper | — |
| SA-0005 | api.bvbrc.query | D-L240-genome, D-L241-genome_feature, D-L246-protein_family_ref | entries/api.bvbrc.query/api; mapped_required_or_scoped_helper | — |
| SA-0006 | api.bvbrc.result | D-L240-genome, D-L241-genome_feature, D-L246-protein_family_ref | entries/api.bvbrc.result/api; mapped_required_or_scoped_helper | — |
| SA-0007 | api.hmmer.check_handoff | A-L065-hmmscan, A-L065-phmmer | entries/api.hmmer.check_handoff/api; mapped_required_or_scoped_helper | — |
| SA-0008 | api.hmmer.databases | A-L065-hmmscan, A-L065-phmmer | entries/api.hmmer.databases/api; mapped_required_or_scoped_helper | — |
| SA-0009 | api.hmmer.prepare | A-L065-hmmscan, A-L065-phmmer | entries/api.hmmer.prepare/api; mapped_required_or_scoped_helper | — |
| SA-0010 | api.hmmer.result | A-L065-hmmscan, A-L065-phmmer | entries/api.hmmer.result/api; mapped_required_or_scoped_helper | — |
| SA-0011 | api.hmmer.status | A-L065-hmmscan, A-L065-phmmer | entries/api.hmmer.status/api; mapped_required_or_scoped_helper | — |
| SA-0012 | api.hmmer.submit | A-L065-hmmscan, A-L065-phmmer | entries/api.hmmer.submit/api; mapped_required_or_scoped_helper | — |
| SA-0013 | api.uniprot.collect | E-L290-uniprot | entries/api.uniprot.collect/api; mapped_required_or_scoped_helper | — |
| SA-0014 | api.uniprot.record | E-L290-uniprot | entries/api.uniprot.record/api; mapped_required_or_scoped_helper | — |
| SA-0015 | api.uniprot.search | E-L290-uniprot | entries/api.uniprot.search/api; mapped_required_or_scoped_helper | — |
| SA-0016 | execution.capabilities | — | entries/execution.capabilities/local; supporting_source_only | — |
| SA-0017 | execution.results.collect | — | entries/execution.results.collect/hpc; supporting_source_only | — |
| SA-0018 | execution.results.collect | — | entries/execution.results.collect/local; supporting_source_only | — |
| SA-0019 | execution.results.read | — | entries/execution.results.read/hpc; supporting_source_only | — |
| SA-0020 | execution.results.read | — | entries/execution.results.read/local; supporting_source_only | — |
| SA-0021 | execution.results.status | — | entries/execution.results.status/hpc; supporting_source_only | — |
| SA-0022 | execution.results.status | — | entries/execution.results.status/local; supporting_source_only | — |
| SA-0023 | genes.predict | A-L062-metagenomic, A-L062-single-genome | entries/genes.predict/local; mapped_required_or_scoped_helper | — |
| SA-0024 | homology.check_handoff | A-L065-phmmer | entries/homology.check_handoff/local; mapped_required_or_scoped_helper | — |
| SA-0025 | homology.configure | A-L065-phmmer | entries/homology.configure/local; mapped_required_or_scoped_helper | — |
| SA-0026 | homology.coverage | A-L065-phmmer | entries/homology.coverage/local; mapped_required_or_scoped_helper | — |
| SA-0027 | homology.environment | A-L065-phmmer | entries/homology.environment/local; mapped_required_or_scoped_helper | — |
| SA-0028 | homology.errors | A-L065-phmmer | entries/homology.errors/local; mapped_required_or_scoped_helper | — |
| SA-0029 | homology.extract | A-L065-phmmer | entries/homology.extract/local; mapped_required_or_scoped_helper | — |
| SA-0030 | homology.resume_start | A-L065-phmmer | entries/homology.resume_start/local; mapped_required_or_scoped_helper | — |
| SA-0031 | homology.sample | A-L065-phmmer | entries/homology.sample/local; mapped_required_or_scoped_helper | — |
| SA-0032 | homology.stage | A-L065-phmmer | entries/homology.stage/local; mapped_required_or_scoped_helper | — |
| SA-0033 | homology.submit | A-L065-phmmer | entries/homology.submit/local; mapped_required_or_scoped_helper | — |
| SA-0034 | image.view | — | entries/image.view/local; excluded_by_current_goal | — |
| SA-0035 | library.members | A-L059-reads | entries/library.members/local; mapped_required_or_scoped_helper | — |
| SA-0036 | library.read | A-L059-reads | entries/library.read/local; mapped_required_or_scoped_helper | — |
| SA-0037 | library.select | A-L059-reads | entries/library.select/local; mapped_required_or_scoped_helper | — |
| SA-0038 | material.annotations | B-L177-inspect_file | entries/material.annotations/local; mapped_required_or_scoped_helper | — |
| SA-0039 | material.errors | B-L177-inspect_file | entries/material.errors/local; mapped_required_or_scoped_helper | — |
| SA-0040 | material.from_source | B-L177-inspect_file | entries/material.from_source/local; mapped_required_or_scoped_helper | — |
| SA-0041 | material.header | B-L177-inspect_file | entries/material.header/local; mapped_required_or_scoped_helper | — |
| SA-0042 | material.member | B-L177-inspect_file | entries/material.member/local; mapped_required_or_scoped_helper | — |
| SA-0043 | material.members | B-L177-inspect_file | entries/material.members/local; mapped_required_or_scoped_helper | — |
| SA-0044 | material.parse | B-L177-inspect_file | entries/material.parse/local; mapped_required_or_scoped_helper | — |
| SA-0045 | material.read | B-L177-inspect_file | entries/material.read/local; mapped_required_or_scoped_helper | — |
| SA-0046 | practical.command.run | — | entries/practical.command.run/hpc; supporting_source_only | — |
| SA-0047 | practical.command.run | — | entries/practical.command.run/local; supporting_source_only | — |
| SA-0048 | practical.context.set | — | entries/practical.context.set/hpc; supporting_source_only | — |
| SA-0049 | practical.context.set | — | entries/practical.context.set/local; supporting_source_only | — |
| SA-0050 | practical.directory.create | — | entries/practical.directory.create/hpc; supporting_source_only | — |
| SA-0051 | practical.directory.create | — | entries/practical.directory.create/local; supporting_source_only | — |
| SA-0052 | practical.file.read | — | entries/practical.file.read/hpc; supporting_source_only | — |
| SA-0053 | practical.file.read | — | entries/practical.file.read/local; supporting_source_only | — |
| SA-0054 | practical.file.write | — | entries/practical.file.write/hpc; supporting_source_only | — |
| SA-0055 | practical.file.write | — | entries/practical.file.write/local; supporting_source_only | — |
| SA-0056 | practical.inspect | — | entries/practical.inspect/hpc; supporting_source_only | — |
| SA-0057 | practical.inspect | — | entries/practical.inspect/local; supporting_source_only | — |
| SA-0058 | practical.inventory.refresh | — | entries/practical.inventory.refresh/hpc; supporting_source_only | — |
| SA-0059 | practical.inventory.refresh | — | entries/practical.inventory.refresh/local; supporting_source_only | — |
| SA-0060 | practical.job.collect | — | entries/practical.job.collect/hpc; supporting_source_only | — |
| SA-0061 | practical.job.collect | — | entries/practical.job.collect/local; supporting_source_only | — |
| SA-0062 | practical.job.start | — | entries/practical.job.start/hpc; supporting_source_only | — |
| SA-0063 | practical.job.start | — | entries/practical.job.start/local; supporting_source_only | — |
| SA-0064 | practical.job.status | — | entries/practical.job.status/hpc; supporting_source_only | — |
| SA-0065 | practical.job.status | — | entries/practical.job.status/local; supporting_source_only | — |
| SA-0066 | progress.log | — | entries/progress.log/api; supporting_source_only | — |
| SA-0067 | progress.log | — | entries/progress.log/hpc; supporting_source_only | — |
| SA-0068 | progress.log | — | entries/progress.log/local; supporting_source_only | — |
| SA-0069 | progress.observe | — | entries/progress.observe/api; supporting_source_only | — |
| SA-0070 | progress.observe | — | entries/progress.observe/hpc; supporting_source_only | — |
| SA-0071 | progress.observe | — | entries/progress.observe/local; supporting_source_only | — |
| SA-0072 | progress.read | — | entries/progress.read/api; supporting_source_only | — |
| SA-0073 | progress.read | — | entries/progress.read/hpc; supporting_source_only | — |
| SA-0074 | progress.read | — | entries/progress.read/local; supporting_source_only | — |
| SA-0075 | public.blast.collect | A-L069-blastn-database, A-L069-blastp-database, A-L069-blastx-database, A-L069-tblastn-database, A-L069-tblastx-database, E-L287-ncbi-blast | entries/public.blast.collect/api; mapped_required_or_scoped_helper | — |
| SA-0076 | public.blast.search | A-L069-blastn-database, A-L069-blastp-database, A-L069-blastx-database, A-L069-tblastn-database, A-L069-tblastx-database, E-L287-ncbi-blast | entries/public.blast.search/api; mapped_required_or_scoped_helper | — |
| SA-0077 | public.chebi.compound | E-L297-chebi | entries/public.chebi.compound/api; mapped_required_or_scoped_helper | — |
| SA-0078 | public.chebi.search | E-L297-chebi | entries/public.chebi.search/api; mapped_required_or_scoped_helper | — |
| SA-0079 | public.literature.read | — | entries/public.literature.read/api; excluded_by_current_goal | — |
| SA-0080 | public.literature.search | — | entries/public.literature.search/api; excluded_by_current_goal | — |
| SA-0081 | public.ncbi.search | E-L288-ncbi-assembly, E-L288-ncbi-gene, E-L288-ncbi-nucleotide, E-L288-ncbi-protein, E-L288-ncbi-taxonomy | entries/public.ncbi.search/api; mapped_required_or_scoped_helper | — |
| SA-0082 | public.ncbi.sequence | E-L288-ncbi-assembly, E-L288-ncbi-gene, E-L288-ncbi-nucleotide, E-L288-ncbi-protein, E-L288-ncbi-taxonomy | entries/public.ncbi.sequence/api; mapped_required_or_scoped_helper | — |
| SA-0083 | public.pmc.asset | — | entries/public.pmc.asset/api; excluded_by_current_goal | — |
| SA-0084 | public.pmc.files | — | entries/public.pmc.files/api; excluded_by_current_goal | — |
| SA-0085 | public.pmc.versions | — | entries/public.pmc.versions/api; excluded_by_current_goal | — |
| SA-0086 | public.rfam.collect | A-L068-rfam-batch | entries/public.rfam.collect/api; mapped_required_or_scoped_helper | — |
| SA-0087 | public.rfam.model | E-L291-rfam | entries/public.rfam.model/api; mapped_required_or_scoped_helper | — |
| SA-0088 | public.rfam.search | A-L068-rfam-batch | entries/public.rfam.search/api; mapped_required_or_scoped_helper | — |
| SA-0089 | public.rhea.reaction | E-L295-rhea | entries/public.rhea.reaction/api; mapped_required_or_scoped_helper | — |
| SA-0090 | public.rhea.search | E-L295-rhea | entries/public.rhea.search/api; mapped_required_or_scoped_helper | — |
| SA-0091 | public.search.jobs | — | entries/public.search.jobs/api; supporting_source_only | — |
| SA-0092 | public.taxonomy | E-L288-ncbi-assembly, E-L288-ncbi-gene, E-L288-ncbi-nucleotide, E-L288-ncbi-protein, E-L288-ncbi-taxonomy | entries/public.taxonomy/api; mapped_required_or_scoped_helper | — |
| SA-0093 | public.uniprot.record | E-L290-uniprot | entries/public.uniprot.record/api; mapped_required_or_scoped_helper | — |
| SA-0094 | public.uniprot.search | E-L290-uniprot | entries/public.uniprot.search/api; mapped_required_or_scoped_helper | — |
| SA-0095 | reads.align | A-L061-dna-global, A-L061-dna-local, A-L061-protein-global, A-L061-protein-local, A-L061-rna-global, A-L061-rna-local | entries/reads.align/local; mapped_required_or_scoped_helper | — |
| SA-0096 | reads.inspect | A-L059-reads, A-L059-sequence | entries/reads.inspect/local; mapped_required_or_scoped_helper | — |
| SA-0097 | reads.map | A-L063-lr-hq, A-L063-map-hifi, A-L063-map-iclr, A-L063-map-ont, A-L063-map-pb, A-L063-sr, A-L064-mapping-correspondence | entries/reads.map/local; mapped_required_or_scoped_helper | — |
| SA-0098 | reference.neighborhood | E-L288-ncbi-nucleotide | entries/reference.neighborhood/local; mapped_required_or_scoped_helper | — |
| SA-0099 | result.blast.hsp | A-L064-blast-hsp, A-L064-mapping-correspondence, A-L064-native-pairwise | entries/result.blast.hsp/local; mapped_required_or_scoped_helper | — |
| SA-0100 | rna.cmsearch | A-L067-cmsearch | entries/rna.cmsearch/local; mapped_required_or_scoped_helper | — |
| SA-0101 | sequence.align | A-L061-dna-global, A-L061-dna-local, A-L061-protein-global, A-L061-protein-local, A-L061-rna-global, A-L061-rna-local | entries/sequence.align/local; mapped_required_or_scoped_helper | — |
| SA-0102 | sequence.inspect | A-L059-reads, A-L059-sequence | entries/sequence.inspect/local; mapped_required_or_scoped_helper | — |
| SA-0103 | sequence.sites | A-L064-blast-hsp, A-L064-mapping-correspondence, A-L064-native-pairwise | entries/sequence.sites/local; mapped_required_or_scoped_helper | — |
| SA-0104 | sequence.translate | A-L060-translation | entries/sequence.translate/local; mapped_required_or_scoped_helper | — |
| SA-0105 | sequence.view | A-L060-extraction, A-L060-translation | entries/sequence.view/local; mapped_required_or_scoped_helper | — |
| SA-0106 | source.archive.extract | — | entries/source.archive.extract/local; excluded_by_current_goal | — |
| SA-0107 | source.archive.members | — | entries/source.archive.members/local; excluded_by_current_goal | — |
| SA-0108 | source.pdf.info | — | entries/source.pdf.info/local; excluded_by_current_goal | — |
| SA-0109 | source.pdf.page | — | entries/source.pdf.page/local; excluded_by_current_goal | — |
| SA-0110 | source.pdf.text | — | entries/source.pdf.text/local; excluded_by_current_goal | — |
| SA-0111 | source.read | B-L177-inspect_file | entries/source.read/local; mapped_required_or_scoped_helper | — |
| SA-0112 | source.xlsx.rows | — | entries/source.xlsx.rows/local; excluded_by_current_goal | — |
| SA-0113 | source.xlsx.sheets | — | entries/source.xlsx.sheets/local; excluded_by_current_goal | — |
| SA-0114 | state.query | B-L177-inspect_file | entries/state.query/local; mapped_required_or_scoped_helper | — |
| SA-0115 | translation.codes | A-L060-extraction, A-L060-translation | entries/translation.codes/local; mapped_required_or_scoped_helper | — |
| SA-0116 | execution.estimate | — | conditional_entries/execution.estimate; supporting_source_only | — |
| SA-0117 | bvbrc_search_data | D-L240-genome, D-L241-genome_feature, D-L242-genome_sequence, D-L246-protein_family_ref, D-L247-protein_feature, D-L248-sequence_feature, D-L249-sequence_feature_vt, D-L250-structured_assertion, D-L253-id_ref, D-L254-taxonomy, D-L257-pathway, D-L258-pathway_ref, D-L259-subsystem, D-L260-subsystem_ref, D-L261-enzyme_class_ref, D-L262-gene_ontology_ref, D-L265-protein_structure, D-L266-ppi, D-L269-experiment, D-L270-bioset, D-L271-bioset_result, D-L273-collection_selection, D-L273-counts, D-L273-exact_identifier_queries, D-L273-existence_checks, D-L273-facets, D-L273-membership_queries, D-L273-pagination, D-L273-ranges, D-L273-selected_fields, D-L273-stable_sorting, D-L273-typed_filters | registered_tools/bvbrc_search_data; mapped_required_or_scoped_helper | — |
| SA-0118 | get_sra_metadata | E-L289-ncbi-sra | registered_tools/get_sra_metadata; mapped_required_or_scoped_helper | — |
| SA-0119 | create_feature_group | — | registered_tools/create_feature_group; supporting_source_only | — |
| SA-0120 | create_genome_group | — | registered_tools/create_genome_group; supporting_source_only | — |
| SA-0121 | get_feature_group_ids | — | registered_tools/get_feature_group_ids; supporting_source_only | — |
| SA-0122 | get_genome_group_ids | — | registered_tools/get_genome_group_ids; supporting_source_only | — |
| SA-0123 | get_job_details | C-L223-status | registered_tools/get_job_details; mapped_required_or_scoped_helper | — |
| SA-0124 | get_service_submission_schema | C-L221-preparation | registered_tools/get_service_submission_schema; mapped_required_or_scoped_helper | — |
| SA-0125 | health_check | — | registered_tools/health_check; supporting_source_only | — |
| SA-0126 | list_jobs | C-L223-status | registered_tools/list_jobs; mapped_required_or_scoped_helper | — |
| SA-0127 | list_service_apps | C-L221-preparation | registered_tools/list_service_apps; mapped_required_or_scoped_helper | — |
| SA-0128 | plan_workflow | — | registered_tools/plan_workflow; excluded_by_current_goal | — |
| SA-0129 | read_file_bytes_tool | C-L224-artifact-acquisition | registered_tools/read_file_bytes_tool; mapped_required_or_scoped_helper | — |
| SA-0130 | read_file_lines | C-L223-status | registered_tools/read_file_lines; mapped_required_or_scoped_helper | — |
| SA-0131 | submit_workflow | — | registered_tools/submit_workflow; excluded_by_current_goal | — |
| SA-0132 | workspace_browse_tool | C-L224-artifact-acquisition | registered_tools/workspace_browse_tool; mapped_required_or_scoped_helper | — |
| SA-0133 | workspace_download_file_tool | C-L224-artifact-acquisition | registered_tools/workspace_download_file_tool; mapped_required_or_scoped_helper | — |
| SA-0134 | workspace_upload | C-L225-input-transfer | registered_tools/workspace_upload; mapped_required_or_scoped_helper | — |
| SA-0135 | helpdesk_service_usage | — | registered_tools/helpdesk_service_usage; excluded_by_current_goal | — |
| SA-0136 | date | C-L217-helper-Date | service_families/date; mapped_required_or_scoped_helper | — |
| SA-0137 | genome_assembly | C-L187-GenomeAssembly2 | service_families/genome_assembly; mapped_required_or_scoped_helper | — |
| SA-0138 | genome_annotation | C-L188-GenomeAnnotation | service_families/genome_annotation; mapped_required_or_scoped_helper | — |
| SA-0139 | comprehensive_genome_analysis | C-L189-ComprehensiveGenomeAnalysis | service_families/comprehensive_genome_analysis; mapped_required_or_scoped_helper | — |
| SA-0140 | blast | C-L190-Homology | service_families/blast; mapped_required_or_scoped_helper | — |
| SA-0141 | primer_design | X-L217-PrimerDesign | service_families/primer_design; excluded_by_current_goal | — |
| SA-0142 | variation | C-L191-Variation | service_families/variation; mapped_required_or_scoped_helper | — |
| SA-0143 | tnseq | C-L192-TnSeq | service_families/tnseq; mapped_required_or_scoped_helper | — |
| SA-0144 | bacterial_genome_tree | C-L193-CodonTree | service_families/bacterial_genome_tree; mapped_required_or_scoped_helper | — |
| SA-0145 | gene_tree | C-L194-GeneTree | service_families/gene_tree; mapped_required_or_scoped_helper | — |
| SA-0146 | core_genome_mlst | C-L195-CoreGenomeMLST | service_families/core_genome_mlst; mapped_required_or_scoped_helper | — |
| SA-0147 | whole_genome_snp | C-L196-WholeGenomeSNPAnalysis | service_families/whole_genome_snp; mapped_required_or_scoped_helper | — |
| SA-0148 | taxonomic_classification | C-L197-TaxonomicClassification | service_families/taxonomic_classification; mapped_required_or_scoped_helper | — |
| SA-0149 | metagenomic_binning | C-L198-MetagenomeBinning | service_families/metagenomic_binning; mapped_required_or_scoped_helper | — |
| SA-0150 | metagenomic_read_mapping | C-L199-MetagenomicReadMapping | service_families/metagenomic_read_mapping; mapped_required_or_scoped_helper | — |
| SA-0151 | rnaseq | C-L200-RNASeq | service_families/rnaseq; mapped_required_or_scoped_helper | — |
| SA-0152 | expression_import | C-L217-helper-ExpressionImport | service_families/expression_import; mapped_required_or_scoped_helper | — |
| SA-0153 | sars_wastewater_analysis | X-L217-SARSWastewaterAnalysis | service_families/sars_wastewater_analysis; excluded_by_current_goal | — |
| SA-0154 | sequence_submission | C-L217-helper-SequenceSubmission | service_families/sequence_submission; mapped_required_or_scoped_helper | — |
| SA-0155 | influenza_ha_subtype_conversion | C-L210-InfluenzaHASubtypeConversion | service_families/influenza_ha_subtype_conversion; mapped_required_or_scoped_helper | — |
| SA-0156 | subspecies_classification | C-L211-SubspeciesClassification | service_families/subspecies_classification; mapped_required_or_scoped_helper | — |
| SA-0157 | viral_assembly | C-L201-ViralAssembly | service_families/viral_assembly; mapped_required_or_scoped_helper | — |
| SA-0158 | genome_alignment | C-L202-GenomeAlignment | service_families/genome_alignment; mapped_required_or_scoped_helper | — |
| SA-0159 | sars_genome_analysis | C-L203-SARS2Assembly | service_families/sars_genome_analysis; mapped_required_or_scoped_helper | — |
| SA-0160 | msa_snp_analysis | C-L204-MSA | service_families/msa_snp_analysis; mapped_required_or_scoped_helper | — |
| SA-0161 | metacats | C-L205-MetaCATS | service_families/metacats; mapped_required_or_scoped_helper | — |
| SA-0162 | proteome_comparison | C-L206-GenomeComparison | service_families/proteome_comparison; mapped_required_or_scoped_helper | — |
| SA-0163 | comparative_systems | C-L207-ComparativeSystems | service_families/comparative_systems; mapped_required_or_scoped_helper | — |
| SA-0164 | docking | X-L217-Docking | service_families/docking; excluded_by_current_goal | — |
| SA-0165 | similar_genome_finder | C-L208-SimilarGenomeFinder, C-L208-minhash-fasta, C-L208-minhash-genome | service_families/similar_genome_finder; mapped_required_or_scoped_helper | — |
| SA-0166 | fastqutils | C-L209-FastqUtils | service_families/fastqutils; mapped_required_or_scoped_helper | — |
| SA-0167 | analyze_circular_dichroism_spectra | B-L150-analyze_circular_dichroism_spectra | biomni_entries/biomni.tool.biochemistry.analyze_circular_dichroism_spectra; mapped_required_or_scoped_helper | — |
| SA-0168 | analyze_rna_secondary_structure_features | B-L104-analyze_rna_secondary_structure_features | biomni_entries/biomni.tool.biochemistry.analyze_rna_secondary_structure_features; mapped_required_or_scoped_helper | — |
| SA-0169 | analyze_protease_kinetics | B-L151-analyze_protease_kinetics | biomni_entries/biomni.tool.biochemistry.analyze_protease_kinetics; mapped_required_or_scoped_helper | — |
| SA-0170 | analyze_enzyme_kinetics_assay | — | biomni_entries/biomni.tool.biochemistry.analyze_enzyme_kinetics_assay; outside_explicit_current_scope | — |
| SA-0171 | analyze_itc_binding_thermodynamics | B-L152-analyze_itc_binding_thermodynamics | biomni_entries/biomni.tool.biochemistry.analyze_itc_binding_thermodynamics; mapped_required_or_scoped_helper | — |
| SA-0172 | analyze_protein_conservation | B-L093-analyze_protein_conservation | biomni_entries/biomni.tool.biochemistry.analyze_protein_conservation; mapped_required_or_scoped_helper | — |
| SA-0173 | analyze_cell_migration_metrics | — | biomni_entries/biomni.tool.bioengineering.analyze_cell_migration_metrics; outside_explicit_current_scope | — |
| SA-0174 | perform_crispr_cas9_genome_editing | — | biomni_entries/biomni.tool.bioengineering.perform_crispr_cas9_genome_editing; outside_explicit_current_scope | — |
| SA-0175 | analyze_calcium_imaging_data | — | biomni_entries/biomni.tool.bioengineering.analyze_calcium_imaging_data; outside_explicit_current_scope | — |
| SA-0176 | analyze_in_vitro_drug_release_kinetics | — | biomni_entries/biomni.tool.bioengineering.analyze_in_vitro_drug_release_kinetics; excluded_by_current_goal | — |
| SA-0177 | analyze_myofiber_morphology | — | biomni_entries/biomni.tool.bioengineering.analyze_myofiber_morphology; outside_explicit_current_scope | — |
| SA-0178 | decode_behavior_from_neural_trajectories | — | biomni_entries/biomni.tool.bioengineering.decode_behavior_from_neural_trajectories; outside_explicit_current_scope | — |
| SA-0179 | simulate_whole_cell_ode_model | — | biomni_entries/biomni.tool.bioengineering.simulate_whole_cell_ode_model; outside_explicit_current_scope | — |
| SA-0180 | split_modalities | — | biomni_entries/biomni.tool.bioimaging.split_modalities; excluded_by_current_goal | — |
| SA-0181 | prepare_input_for_nnunet | — | biomni_entries/biomni.tool.bioimaging.prepare_input_for_nnunet; excluded_by_current_goal | — |
| SA-0182 | segment_with_nn_unet | — | biomni_entries/biomni.tool.bioimaging.segment_with_nn_unet; excluded_by_current_goal | — |
| SA-0183 | create_segmentation_visualization | — | biomni_entries/biomni.tool.bioimaging.create_segmentation_visualization; excluded_by_current_goal | — |
| SA-0184 | quick_rigid_registration | — | biomni_entries/biomni.tool.bioimaging.quick_rigid_registration; excluded_by_current_goal | — |
| SA-0185 | quick_affine_registration | — | biomni_entries/biomni.tool.bioimaging.quick_affine_registration; excluded_by_current_goal | — |
| SA-0186 | quick_deformable_registration | — | biomni_entries/biomni.tool.bioimaging.quick_deformable_registration; excluded_by_current_goal | — |
| SA-0187 | batch_register_images | — | biomni_entries/biomni.tool.bioimaging.batch_register_images; excluded_by_current_goal | — |
| SA-0188 | calculate_similarity_metrics | — | biomni_entries/biomni.tool.bioimaging.calculate_similarity_metrics; excluded_by_current_goal | — |
| SA-0189 | create_registration_visualization | — | biomni_entries/biomni.tool.bioimaging.create_registration_visualization; excluded_by_current_goal | — |
| SA-0190 | predict_protein_disorder_regions | B-L097-predict_protein_disorder_regions | biomni_entries/biomni.tool.biophysics.predict_protein_disorder_regions; mapped_required_or_scoped_helper | — |
| SA-0191 | analyze_cell_morphology_and_cytoskeleton | — | biomni_entries/biomni.tool.biophysics.analyze_cell_morphology_and_cytoskeleton; outside_explicit_current_scope | — |
| SA-0192 | analyze_tissue_deformation_flow | — | biomni_entries/biomni.tool.biophysics.analyze_tissue_deformation_flow; outside_explicit_current_scope | — |
| SA-0193 | analyze_ddr_network_in_cancer | — | biomni_entries/biomni.tool.cancer_biology.analyze_ddr_network_in_cancer; outside_explicit_current_scope | — |
| SA-0194 | analyze_cell_senescence_and_apoptosis | — | biomni_entries/biomni.tool.cancer_biology.analyze_cell_senescence_and_apoptosis; outside_explicit_current_scope | — |
| SA-0195 | detect_and_annotate_somatic_mutations | B-L111-detect_and_annotate_somatic_mutations | biomni_entries/biomni.tool.cancer_biology.detect_and_annotate_somatic_mutations; mapped_required_or_scoped_helper | — |
| SA-0196 | detect_and_characterize_structural_variations | B-L112-detect_and_characterize_structural_variations | biomni_entries/biomni.tool.cancer_biology.detect_and_characterize_structural_variations; mapped_required_or_scoped_helper | — |
| SA-0197 | perform_gene_expression_nmf_analysis | B-L128-perform_gene_expression_nmf_analysis | biomni_entries/biomni.tool.cancer_biology.perform_gene_expression_nmf_analysis; mapped_required_or_scoped_helper | — |
| SA-0198 | analyze_copy_number_purity_ploidy_and_focal_events | B-L113-analyze_copy_number_purity_ploidy_and_focal_events | biomni_entries/biomni.tool.cancer_biology.analyze_copy_number_purity_ploidy_and_focal_events; mapped_required_or_scoped_helper | — |
| SA-0199 | quantify_cell_cycle_phases_from_microscopy | — | biomni_entries/biomni.tool.cell_biology.quantify_cell_cycle_phases_from_microscopy; outside_explicit_current_scope | — |
| SA-0200 | quantify_and_cluster_cell_motility | — | biomni_entries/biomni.tool.cell_biology.quantify_and_cluster_cell_motility; outside_explicit_current_scope | — |
| SA-0201 | perform_facs_cell_sorting | B-L159-perform_facs_cell_sorting | biomni_entries/biomni.tool.cell_biology.perform_facs_cell_sorting; mapped_required_or_scoped_helper | — |
| SA-0202 | analyze_flow_cytometry_immunophenotyping | — | biomni_entries/biomni.tool.cell_biology.analyze_flow_cytometry_immunophenotyping; outside_explicit_current_scope | — |
| SA-0203 | analyze_mitochondrial_morphology_and_potential | — | biomni_entries/biomni.tool.cell_biology.analyze_mitochondrial_morphology_and_potential; outside_explicit_current_scope | — |
| SA-0204 | query_uniprot | E-L290-uniprot, E-L309-query_uniprot | biomni_entries/biomni.tool.database.query_uniprot; mapped_required_or_scoped_helper | — |
| SA-0205 | query_alphafold | E-L292-alphafold-protein-structure-database, E-L309-query_alphafold | biomni_entries/biomni.tool.database.query_alphafold; mapped_required_or_scoped_helper | — |
| SA-0206 | query_interpro | E-L291-interpro, E-L309-query_interpro | biomni_entries/biomni.tool.database.query_interpro; mapped_required_or_scoped_helper | — |
| SA-0207 | query_pdb | E-L293-rcsb-pdb, E-L309-query_pdb | biomni_entries/biomni.tool.database.query_pdb; mapped_required_or_scoped_helper | — |
| SA-0208 | query_pdb_identifiers | E-L293-rcsb-pdb, E-L309-query_pdb_identifiers | biomni_entries/biomni.tool.database.query_pdb_identifiers; mapped_required_or_scoped_helper | — |
| SA-0209 | query_kegg | E-L295-kegg, E-L309-query_kegg | biomni_entries/biomni.tool.database.query_kegg; mapped_required_or_scoped_helper | — |
| SA-0210 | query_stringdb | E-L294-string, E-L309-query_stringdb | biomni_entries/biomni.tool.database.query_stringdb; mapped_required_or_scoped_helper | — |
| SA-0211 | query_iucn | — | biomni_entries/biomni.tool.database.query_iucn; outside_explicit_current_scope | — |
| SA-0212 | query_paleobiology | — | biomni_entries/biomni.tool.database.query_paleobiology; outside_explicit_current_scope | — |
| SA-0213 | query_jaspar | E-L299-jaspar, E-L309-query_jaspar | biomni_entries/biomni.tool.database.query_jaspar; mapped_required_or_scoped_helper | — |
| SA-0214 | query_worms | — | biomni_entries/biomni.tool.database.query_worms; outside_explicit_current_scope | — |
| SA-0215 | query_cbioportal | E-L303-cbioportal, E-L309-query_cbioportal | biomni_entries/biomni.tool.database.query_cbioportal; mapped_required_or_scoped_helper | — |
| SA-0216 | query_clinvar | — | biomni_entries/biomni.tool.database.query_clinvar; outside_explicit_current_scope | — |
| SA-0217 | query_geo | E-L289-ncbi-geo, E-L309-query_geo | biomni_entries/biomni.tool.database.query_geo; mapped_required_or_scoped_helper | — |
| SA-0218 | query_dbsnp | E-L298-dbsnp, E-L309-query_dbsnp | biomni_entries/biomni.tool.database.query_dbsnp; mapped_required_or_scoped_helper | — |
| SA-0219 | query_ucsc | E-L298-ucsc, E-L309-query_ucsc | biomni_entries/biomni.tool.database.query_ucsc; mapped_required_or_scoped_helper | — |
| SA-0220 | query_ensembl | E-L298-ensembl, E-L309-query_ensembl | biomni_entries/biomni.tool.database.query_ensembl; mapped_required_or_scoped_helper | — |
| SA-0221 | query_opentarget | — | biomni_entries/biomni.tool.database.query_opentarget; outside_explicit_current_scope | — |
| SA-0222 | query_monarch | — | biomni_entries/biomni.tool.database.query_monarch; outside_explicit_current_scope | — |
| SA-0223 | query_openfda | — | biomni_entries/biomni.tool.database.query_openfda; outside_explicit_current_scope | — |
| SA-0224 | query_gwas_catalog | — | biomni_entries/biomni.tool.database.query_gwas_catalog; excluded_by_current_goal | — |
| SA-0225 | query_gnomad | E-L298-gnomad, E-L309-query_gnomad | biomni_entries/biomni.tool.database.query_gnomad; mapped_required_or_scoped_helper | — |
| SA-0226 | blast_sequence | B-L090-blast_sequence | biomni_entries/biomni.tool.database.blast_sequence; mapped_required_or_scoped_helper | — |
| SA-0227 | query_reactome | E-L295-reactome, E-L309-query_reactome | biomni_entries/biomni.tool.database.query_reactome; mapped_required_or_scoped_helper | — |
| SA-0228 | query_regulomedb | E-L299-regulomedb, E-L309-query_regulomedb | biomni_entries/biomni.tool.database.query_regulomedb; mapped_required_or_scoped_helper | — |
| SA-0229 | query_pride | E-L304-pride, E-L309-query_pride | biomni_entries/biomni.tool.database.query_pride; mapped_required_or_scoped_helper | — |
| SA-0230 | query_gtopdb | — | biomni_entries/biomni.tool.database.query_gtopdb; outside_explicit_current_scope | — |
| SA-0231 | query_remap | E-L299-remap, E-L309-query_remap | biomni_entries/biomni.tool.database.query_remap; mapped_required_or_scoped_helper | — |
| SA-0232 | query_mpd | — | biomni_entries/biomni.tool.database.query_mpd; outside_explicit_current_scope | — |
| SA-0233 | query_emdb | E-L293-emdb, E-L309-query_emdb | biomni_entries/biomni.tool.database.query_emdb; mapped_required_or_scoped_helper | — |
| SA-0234 | query_synapse | E-L307-synapse, E-L309-query_synapse | biomni_entries/biomni.tool.database.query_synapse; mapped_required_or_scoped_helper | — |
| SA-0235 | query_pubchem | E-L297-pubchem, E-L309-query_pubchem | biomni_entries/biomni.tool.database.query_pubchem; mapped_required_or_scoped_helper | — |
| SA-0236 | query_chembl | — | biomni_entries/biomni.tool.database.query_chembl; outside_explicit_current_scope | — |
| SA-0237 | query_unichem | — | biomni_entries/biomni.tool.database.query_unichem; outside_explicit_current_scope | — |
| SA-0238 | query_clinicaltrials | — | biomni_entries/biomni.tool.database.query_clinicaltrials; excluded_by_current_goal | — |
| SA-0239 | query_dailymed | — | biomni_entries/biomni.tool.database.query_dailymed; outside_explicit_current_scope | — |
| SA-0240 | query_quickgo | E-L296-quickgo, E-L309-query_quickgo | biomni_entries/biomni.tool.database.query_quickgo; mapped_required_or_scoped_helper | — |
| SA-0241 | query_encode | E-L299-encode, E-L309-query_encode | biomni_entries/biomni.tool.database.query_encode; mapped_required_or_scoped_helper | — |
| SA-0242 | region_to_ccre_screen | E-L299-ccre-data, E-L309-region_to_ccre_screen | biomni_entries/biomni.tool.database.region_to_ccre_screen; mapped_required_or_scoped_helper | — |
| SA-0243 | get_genes_near_ccre | E-L299-ccre-data, E-L309-get_genes_near_ccre | biomni_entries/biomni.tool.database.get_genes_near_ccre; mapped_required_or_scoped_helper | — |
| SA-0244 | liftover_coordinates | B-L110-liftover_coordinates | biomni_entries/biomni.tool.genetics.liftover_coordinates; mapped_required_or_scoped_helper | — |
| SA-0245 | bayesian_finemapping_with_deep_vi | — | biomni_entries/biomni.tool.genetics.bayesian_finemapping_with_deep_vi; outside_explicit_current_scope | — |
| SA-0246 | analyze_cas9_mutation_outcomes | B-L114-analyze_cas9_mutation_outcomes | biomni_entries/biomni.tool.genetics.analyze_cas9_mutation_outcomes; mapped_required_or_scoped_helper | — |
| SA-0247 | analyze_crispr_genome_editing | B-L115-analyze_crispr_genome_editing | biomni_entries/biomni.tool.genetics.analyze_crispr_genome_editing; mapped_required_or_scoped_helper | — |
| SA-0248 | simulate_demographic_history | — | biomni_entries/biomni.tool.genetics.simulate_demographic_history; outside_explicit_current_scope | — |
| SA-0249 | identify_transcription_factor_binding_sites | B-L120-identify_transcription_factor_binding_sites | biomni_entries/biomni.tool.genetics.identify_transcription_factor_binding_sites; mapped_required_or_scoped_helper | — |
| SA-0250 | fit_genomic_prediction_model | — | biomni_entries/biomni.tool.genetics.fit_genomic_prediction_model; outside_explicit_current_scope | — |
| SA-0251 | perform_pcr_and_gel_electrophoresis | — | biomni_entries/biomni.tool.genetics.perform_pcr_and_gel_electrophoresis; outside_explicit_current_scope | — |
| SA-0252 | analyze_protein_phylogeny | B-L094-analyze_protein_phylogeny | biomni_entries/biomni.tool.genetics.analyze_protein_phylogeny; mapped_required_or_scoped_helper | — |
| SA-0253 | annotate_celltype_scRNA | — | biomni_entries/biomni.tool.genomics.annotate_celltype_scRNA; excluded_by_current_goal | — |
| SA-0254 | annotate_celltype_with_panhumanpy | B-L133-annotate_celltype_with_panhumanpy | biomni_entries/biomni.tool.genomics.annotate_celltype_with_panhumanpy; mapped_required_or_scoped_helper | — |
| SA-0255 | create_scvi_embeddings_scRNA | B-L134-create_scvi_embeddings_scRNA | biomni_entries/biomni.tool.genomics.create_scvi_embeddings_scRNA; mapped_required_or_scoped_helper | — |
| SA-0256 | create_harmony_embeddings_scRNA | B-L135-create_harmony_embeddings_scRNA | biomni_entries/biomni.tool.genomics.create_harmony_embeddings_scRNA; mapped_required_or_scoped_helper | — |
| SA-0257 | get_uce_embeddings_scRNA | B-L136-get_uce_embeddings_scRNA | biomni_entries/biomni.tool.genomics.get_uce_embeddings_scRNA; mapped_required_or_scoped_helper | — |
| SA-0258 | map_to_ima_interpret_scRNA | B-L137-map_to_ima_interpret_scRNA | biomni_entries/biomni.tool.genomics.map_to_ima_interpret_scRNA; mapped_required_or_scoped_helper | — |
| SA-0259 | get_rna_seq_archs4 | B-L173-get_rna_seq_archs4, E-L300-archs4 | biomni_entries/biomni.tool.genomics.get_rna_seq_archs4; mapped_required_or_scoped_helper | — |
| SA-0260 | get_gene_set_enrichment_analysis_supported_database_list | B-L175-get_gene_set_enrichment_analysis_supported_database_list | biomni_entries/biomni.tool.genomics.get_gene_set_enrichment_analysis_supported_database_list; mapped_required_or_scoped_helper | — |
| SA-0261 | gene_set_enrichment_analysis | B-L129-gene_set_enrichment_analysis | biomni_entries/biomni.tool.genomics.gene_set_enrichment_analysis; mapped_required_or_scoped_helper | — |
| SA-0262 | analyze_chromatin_interactions | B-L124-analyze_chromatin_interactions | biomni_entries/biomni.tool.genomics.analyze_chromatin_interactions; mapped_required_or_scoped_helper | — |
| SA-0263 | analyze_comparative_genomics_and_haplotypes | X-L329-fabricated-comparative-wrapper | biomni_entries/biomni.tool.genomics.analyze_comparative_genomics_and_haplotypes; excluded_by_current_goal | — |
| SA-0264 | perform_chipseq_peak_calling_with_macs2 | B-L121-perform_chipseq_peak_calling_with_macs2 | biomni_entries/biomni.tool.genomics.perform_chipseq_peak_calling_with_macs2; mapped_required_or_scoped_helper | — |
| SA-0265 | find_enriched_motifs_with_homer | B-L122-find_enriched_motifs_with_homer | biomni_entries/biomni.tool.genomics.find_enriched_motifs_with_homer; mapped_required_or_scoped_helper | — |
| SA-0266 | analyze_genomic_region_overlap | B-L123-analyze_genomic_region_overlap | biomni_entries/biomni.tool.genomics.analyze_genomic_region_overlap; mapped_required_or_scoped_helper | — |
| SA-0267 | unsupervised_celltype_transfer_between_scRNA_datasets | B-L138-unsupervised_celltype_transfer_between_scRNA_datasets | biomni_entries/biomni.tool.genomics.unsupervised_celltype_transfer_between_scRNA_datasets; mapped_required_or_scoped_helper | — |
| SA-0268 | generate_embeddings_with_state | B-L139-generate_embeddings_with_state | biomni_entries/biomni.tool.genomics.generate_embeddings_with_state; mapped_required_or_scoped_helper | — |
| SA-0269 | interspecies_gene_conversion | B-L174-interspecies_gene_conversion, E-L298-ensembl | biomni_entries/biomni.tool.genomics.interspecies_gene_conversion; mapped_required_or_scoped_helper | — |
| SA-0270 | generate_gene_embeddings_with_ESM_models | B-L145-generate_gene_embeddings_with_ESM_models | biomni_entries/biomni.tool.genomics.generate_gene_embeddings_with_ESM_models; mapped_required_or_scoped_helper | — |
| SA-0271 | generate_transcriptformer_embeddings | B-L140-generate_transcriptformer_embeddings | biomni_entries/biomni.tool.genomics.generate_transcriptformer_embeddings; mapped_required_or_scoped_helper | — |
| SA-0272 | find_n_glycosylation_motifs | B-L099-find_n_glycosylation_motifs | biomni_entries/biomni.tool.glycoengineering.find_n_glycosylation_motifs; mapped_required_or_scoped_helper | — |
| SA-0273 | predict_o_glycosylation_hotspots | B-L100-predict_o_glycosylation_hotspots | biomni_entries/biomni.tool.glycoengineering.predict_o_glycosylation_hotspots; mapped_required_or_scoped_helper | — |
| SA-0274 | list_glycoengineering_resources | — | biomni_entries/biomni.tool.glycoengineering.list_glycoengineering_resources; outside_explicit_current_scope | — |
| SA-0275 | analyze_atac_seq_differential_accessibility | B-L125-analyze_atac_seq_differential_accessibility | biomni_entries/biomni.tool.immunology.analyze_atac_seq_differential_accessibility; mapped_required_or_scoped_helper | — |
| SA-0276 | analyze_bacterial_growth_curve | — | biomni_entries/biomni.tool.immunology.analyze_bacterial_growth_curve; outside_explicit_current_scope | — |
| SA-0277 | isolate_purify_immune_cells | — | biomni_entries/biomni.tool.immunology.isolate_purify_immune_cells; outside_explicit_current_scope | — |
| SA-0278 | estimate_cell_cycle_phase_durations | — | biomni_entries/biomni.tool.immunology.estimate_cell_cycle_phase_durations; outside_explicit_current_scope | — |
| SA-0279 | track_immune_cells_under_flow | — | biomni_entries/biomni.tool.immunology.track_immune_cells_under_flow; outside_explicit_current_scope | — |
| SA-0280 | analyze_cfse_cell_proliferation | — | biomni_entries/biomni.tool.immunology.analyze_cfse_cell_proliferation; outside_explicit_current_scope | — |
| SA-0281 | analyze_cytokine_production_in_cd4_tcells | B-L158-analyze_cytokine_production_in_cd4_tcells | biomni_entries/biomni.tool.immunology.analyze_cytokine_production_in_cd4_tcells; mapped_required_or_scoped_helper | — |
| SA-0282 | analyze_ebv_antibody_titers | — | biomni_entries/biomni.tool.immunology.analyze_ebv_antibody_titers; outside_explicit_current_scope | — |
| SA-0283 | analyze_cns_lesion_histology | — | biomni_entries/biomni.tool.immunology.analyze_cns_lesion_histology; outside_explicit_current_scope | — |
| SA-0284 | analyze_immunohistochemistry_image | — | biomni_entries/biomni.tool.immunology.analyze_immunohistochemistry_image; outside_explicit_current_scope | — |
| SA-0285 | test_pylabrobot_script | — | biomni_entries/biomni.tool.lab_automation.test_pylabrobot_script; outside_explicit_current_scope | — |
| SA-0286 | get_pylabrobot_documentation_liquid | — | biomni_entries/biomni.tool.lab_automation.get_pylabrobot_documentation_liquid; outside_explicit_current_scope | — |
| SA-0287 | get_pylabrobot_documentation_material | — | biomni_entries/biomni.tool.lab_automation.get_pylabrobot_documentation_material; outside_explicit_current_scope | — |
| SA-0288 | fetch_supplementary_info_from_doi | — | biomni_entries/biomni.tool.literature.fetch_supplementary_info_from_doi; excluded_by_current_goal | — |
| SA-0289 | query_arxiv | — | biomni_entries/biomni.tool.literature.query_arxiv; excluded_by_current_goal | — |
| SA-0290 | query_scholar | — | biomni_entries/biomni.tool.literature.query_scholar; excluded_by_current_goal | — |
| SA-0291 | query_pubmed | — | biomni_entries/biomni.tool.literature.query_pubmed; excluded_by_current_goal | — |
| SA-0292 | search_google | — | biomni_entries/biomni.tool.literature.search_google; excluded_by_current_goal | — |
| SA-0293 | extract_url_content | — | biomni_entries/biomni.tool.literature.extract_url_content; excluded_by_current_goal | — |
| SA-0294 | extract_pdf_content | — | biomni_entries/biomni.tool.literature.extract_pdf_content; excluded_by_current_goal | — |
| SA-0295 | advanced_web_search_claude | — | biomni_entries/biomni.tool.literature.advanced_web_search_claude; excluded_by_current_goal | — |
| SA-0296 | optimize_anaerobic_digestion_process | — | biomni_entries/biomni.tool.microbiology.optimize_anaerobic_digestion_process; outside_explicit_current_scope | — |
| SA-0297 | analyze_arsenic_speciation_hplc_icpms | B-L153-analyze_arsenic_speciation_hplc_icpms | biomni_entries/biomni.tool.microbiology.analyze_arsenic_speciation_hplc_icpms; mapped_required_or_scoped_helper | — |
| SA-0298 | count_bacterial_colonies | — | biomni_entries/biomni.tool.microbiology.count_bacterial_colonies; outside_explicit_current_scope | — |
| SA-0299 | annotate_bacterial_genome | B-L089-annotate_bacterial_genome | biomni_entries/biomni.tool.microbiology.annotate_bacterial_genome; mapped_required_or_scoped_helper | — |
| SA-0300 | enumerate_bacterial_cfu_by_serial_dilution | — | biomni_entries/biomni.tool.microbiology.enumerate_bacterial_cfu_by_serial_dilution; outside_explicit_current_scope | — |
| SA-0301 | model_bacterial_growth_dynamics | — | biomni_entries/biomni.tool.microbiology.model_bacterial_growth_dynamics; outside_explicit_current_scope | — |
| SA-0302 | quantify_biofilm_biomass_crystal_violet | — | biomni_entries/biomni.tool.microbiology.quantify_biofilm_biomass_crystal_violet; outside_explicit_current_scope | — |
| SA-0303 | segment_and_analyze_microbial_cells | — | biomni_entries/biomni.tool.microbiology.segment_and_analyze_microbial_cells; outside_explicit_current_scope | — |
| SA-0304 | segment_cells_with_deep_learning | — | biomni_entries/biomni.tool.microbiology.segment_cells_with_deep_learning; outside_explicit_current_scope | — |
| SA-0305 | simulate_generalized_lotka_volterra_dynamics | — | biomni_entries/biomni.tool.microbiology.simulate_generalized_lotka_volterra_dynamics; outside_explicit_current_scope | — |
| SA-0306 | predict_rna_secondary_structure | B-L103-predict_rna_secondary_structure | biomni_entries/biomni.tool.microbiology.predict_rna_secondary_structure; mapped_required_or_scoped_helper | — |
| SA-0307 | simulate_microbial_population_dynamics | — | biomni_entries/biomni.tool.microbiology.simulate_microbial_population_dynamics; outside_explicit_current_scope | — |
| SA-0308 | annotate_open_reading_frames | B-L087-annotate_open_reading_frames | biomni_entries/biomni.tool.molecular_biology.annotate_open_reading_frames; mapped_required_or_scoped_helper | — |
| SA-0309 | annotate_plasmid | B-L088-annotate_plasmid | biomni_entries/biomni.tool.molecular_biology.annotate_plasmid; mapped_required_or_scoped_helper | — |
| SA-0310 | get_gene_coding_sequence | B-L169-get_gene_coding_sequence | biomni_entries/biomni.tool.molecular_biology.get_gene_coding_sequence; mapped_required_or_scoped_helper | — |
| SA-0311 | get_plasmid_sequence | B-L170-get_plasmid_sequence | biomni_entries/biomni.tool.molecular_biology.get_plasmid_sequence; mapped_required_or_scoped_helper | — |
| SA-0312 | align_sequences | B-L091-align_sequences | biomni_entries/biomni.tool.molecular_biology.align_sequences; mapped_required_or_scoped_helper | — |
| SA-0313 | pcr_simple | — | biomni_entries/biomni.tool.molecular_biology.pcr_simple; outside_explicit_current_scope | — |
| SA-0314 | digest_sequence | — | biomni_entries/biomni.tool.molecular_biology.digest_sequence; outside_explicit_current_scope | — |
| SA-0315 | find_restriction_sites | B-L171-find_restriction_sites | biomni_entries/biomni.tool.molecular_biology.find_restriction_sites; mapped_required_or_scoped_helper | — |
| SA-0316 | find_restriction_enzymes | B-L172-find_restriction_enzymes | biomni_entries/biomni.tool.molecular_biology.find_restriction_enzymes; mapped_required_or_scoped_helper | — |
| SA-0317 | find_sequence_mutations | B-L092-find_sequence_mutations | biomni_entries/biomni.tool.molecular_biology.find_sequence_mutations; mapped_required_or_scoped_helper | — |
| SA-0318 | design_knockout_sgrna | — | biomni_entries/biomni.tool.molecular_biology.design_knockout_sgrna; excluded_by_current_goal | — |
| SA-0319 | get_oligo_annealing_protocol | — | biomni_entries/biomni.tool.molecular_biology.get_oligo_annealing_protocol; outside_explicit_current_scope | — |
| SA-0320 | get_golden_gate_assembly_protocol | — | biomni_entries/biomni.tool.molecular_biology.get_golden_gate_assembly_protocol; outside_explicit_current_scope | — |
| SA-0321 | get_bacterial_transformation_protocol | — | biomni_entries/biomni.tool.molecular_biology.get_bacterial_transformation_protocol; outside_explicit_current_scope | — |
| SA-0322 | design_primer | — | biomni_entries/biomni.tool.molecular_biology.design_primer; excluded_by_current_goal | — |
| SA-0323 | design_verification_primers | — | biomni_entries/biomni.tool.molecular_biology.design_verification_primers; excluded_by_current_goal | — |
| SA-0324 | design_golden_gate_oligos | — | biomni_entries/biomni.tool.molecular_biology.design_golden_gate_oligos; outside_explicit_current_scope | — |
| SA-0325 | golden_gate_assembly | — | biomni_entries/biomni.tool.molecular_biology.golden_gate_assembly; outside_explicit_current_scope | — |
| SA-0326 | analyze_aortic_diameter_and_geometry | — | biomni_entries/biomni.tool.pathology.analyze_aortic_diameter_and_geometry; excluded_by_current_goal | — |
| SA-0327 | analyze_atp_luminescence_assay | — | biomni_entries/biomni.tool.pathology.analyze_atp_luminescence_assay; excluded_by_current_goal | — |
| SA-0328 | analyze_thrombus_histology | — | biomni_entries/biomni.tool.pathology.analyze_thrombus_histology; excluded_by_current_goal | — |
| SA-0329 | analyze_intracellular_calcium_with_rhod2 | — | biomni_entries/biomni.tool.pathology.analyze_intracellular_calcium_with_rhod2; excluded_by_current_goal | — |
| SA-0330 | quantify_corneal_nerve_fibers | — | biomni_entries/biomni.tool.pathology.quantify_corneal_nerve_fibers; excluded_by_current_goal | — |
| SA-0331 | segment_and_quantify_cells_in_multiplexed_images | — | biomni_entries/biomni.tool.pathology.segment_and_quantify_cells_in_multiplexed_images; excluded_by_current_goal | — |
| SA-0332 | analyze_bone_microct_morphometry | — | biomni_entries/biomni.tool.pathology.analyze_bone_microct_morphometry; excluded_by_current_goal | — |
| SA-0333 | run_diffdock_with_smiles | — | biomni_entries/biomni.tool.pharmacology.run_diffdock_with_smiles; excluded_by_current_goal | — |
| SA-0334 | docking_autodock_vina | — | biomni_entries/biomni.tool.pharmacology.docking_autodock_vina; excluded_by_current_goal | — |
| SA-0335 | run_autosite | — | biomni_entries/biomni.tool.pharmacology.run_autosite; excluded_by_current_goal | — |
| SA-0336 | retrieve_topk_repurposing_drugs_from_disease_txgnn | — | biomni_entries/biomni.tool.pharmacology.retrieve_topk_repurposing_drugs_from_disease_txgnn; excluded_by_current_goal | — |
| SA-0337 | predict_admet_properties | — | biomni_entries/biomni.tool.pharmacology.predict_admet_properties; excluded_by_current_goal | — |
| SA-0338 | predict_binding_affinity_protein_1d_sequence | — | biomni_entries/biomni.tool.pharmacology.predict_binding_affinity_protein_1d_sequence; excluded_by_current_goal | — |
| SA-0339 | analyze_accelerated_stability_of_pharmaceutical_formulations | — | biomni_entries/biomni.tool.pharmacology.analyze_accelerated_stability_of_pharmaceutical_formulations; excluded_by_current_goal | — |
| SA-0340 | run_3d_chondrogenic_aggregate_assay | — | biomni_entries/biomni.tool.pharmacology.run_3d_chondrogenic_aggregate_assay; excluded_by_current_goal | — |
| SA-0341 | grade_adverse_events_using_vcog_ctcae | — | biomni_entries/biomni.tool.pharmacology.grade_adverse_events_using_vcog_ctcae; excluded_by_current_goal | — |
| SA-0342 | analyze_radiolabeled_antibody_biodistribution | — | biomni_entries/biomni.tool.pharmacology.analyze_radiolabeled_antibody_biodistribution; excluded_by_current_goal | — |
| SA-0343 | estimate_alpha_particle_radiotherapy_dosimetry | — | biomni_entries/biomni.tool.pharmacology.estimate_alpha_particle_radiotherapy_dosimetry; excluded_by_current_goal | — |
| SA-0344 | perform_mwas_cyp2c19_metabolizer_status | — | biomni_entries/biomni.tool.pharmacology.perform_mwas_cyp2c19_metabolizer_status; excluded_by_current_goal | — |
| SA-0345 | calculate_physicochemical_properties | — | biomni_entries/biomni.tool.pharmacology.calculate_physicochemical_properties; excluded_by_current_goal | — |
| SA-0346 | analyze_xenograft_tumor_growth_inhibition | — | biomni_entries/biomni.tool.pharmacology.analyze_xenograft_tumor_growth_inhibition; excluded_by_current_goal | — |
| SA-0347 | analyze_western_blot | — | biomni_entries/biomni.tool.pharmacology.analyze_western_blot; excluded_by_current_goal | — |
| SA-0348 | query_drug_interactions | — | biomni_entries/biomni.tool.pharmacology.query_drug_interactions; excluded_by_current_goal | — |
| SA-0349 | check_drug_combination_safety | — | biomni_entries/biomni.tool.pharmacology.check_drug_combination_safety; excluded_by_current_goal | — |
| SA-0350 | analyze_interaction_mechanisms | — | biomni_entries/biomni.tool.pharmacology.analyze_interaction_mechanisms; excluded_by_current_goal | — |
| SA-0351 | find_alternative_drugs_ddinter | — | biomni_entries/biomni.tool.pharmacology.find_alternative_drugs_ddinter; excluded_by_current_goal | — |
| SA-0352 | query_fda_adverse_events | — | biomni_entries/biomni.tool.pharmacology.query_fda_adverse_events; excluded_by_current_goal | — |
| SA-0353 | get_fda_drug_label_info | — | biomni_entries/biomni.tool.pharmacology.get_fda_drug_label_info; excluded_by_current_goal | — |
| SA-0354 | check_fda_drug_recalls | — | biomni_entries/biomni.tool.pharmacology.check_fda_drug_recalls; excluded_by_current_goal | — |
| SA-0355 | analyze_fda_safety_signals | — | biomni_entries/biomni.tool.pharmacology.analyze_fda_safety_signals; excluded_by_current_goal | — |
| SA-0356 | reconstruct_3d_face_from_mri | — | biomni_entries/biomni.tool.physiology.reconstruct_3d_face_from_mri; excluded_by_current_goal | — |
| SA-0357 | analyze_abr_waveform_p1_metrics | — | biomni_entries/biomni.tool.physiology.analyze_abr_waveform_p1_metrics; excluded_by_current_goal | — |
| SA-0358 | analyze_ciliary_beat_frequency | — | biomni_entries/biomni.tool.physiology.analyze_ciliary_beat_frequency; excluded_by_current_goal | — |
| SA-0359 | analyze_protein_colocalization | — | biomni_entries/biomni.tool.physiology.analyze_protein_colocalization; excluded_by_current_goal | — |
| SA-0360 | perform_cosinor_analysis | — | biomni_entries/biomni.tool.physiology.perform_cosinor_analysis; excluded_by_current_goal | — |
| SA-0361 | calculate_brain_adc_map | — | biomni_entries/biomni.tool.physiology.calculate_brain_adc_map; excluded_by_current_goal | — |
| SA-0362 | analyze_endolysosomal_calcium_dynamics | — | biomni_entries/biomni.tool.physiology.analyze_endolysosomal_calcium_dynamics; excluded_by_current_goal | — |
| SA-0363 | analyze_fatty_acid_composition_by_gc | — | biomni_entries/biomni.tool.physiology.analyze_fatty_acid_composition_by_gc; excluded_by_current_goal | — |
| SA-0364 | analyze_hemodynamic_data | — | biomni_entries/biomni.tool.physiology.analyze_hemodynamic_data; excluded_by_current_goal | — |
| SA-0365 | simulate_thyroid_hormone_pharmacokinetics | — | biomni_entries/biomni.tool.physiology.simulate_thyroid_hormone_pharmacokinetics; excluded_by_current_goal | — |
| SA-0366 | quantify_amyloid_beta_plaques | — | biomni_entries/biomni.tool.physiology.quantify_amyloid_beta_plaques; excluded_by_current_goal | — |
| SA-0367 | run_python_repl | — | biomni_entries/biomni.tool.support_tools.run_python_repl; outside_explicit_current_scope | — |
| SA-0368 | read_function_source_code | — | biomni_entries/biomni.tool.support_tools.read_function_source_code; outside_explicit_current_scope | — |
| SA-0369 | download_synapse_data | E-L307-synapse | biomni_entries/biomni.tool.support_tools.download_synapse_data; mapped_required_or_scoped_helper | — |
| SA-0370 | engineer_bacterial_genome_for_therapeutic_delivery | — | biomni_entries/biomni.tool.synthetic_biology.engineer_bacterial_genome_for_therapeutic_delivery; outside_explicit_current_scope | — |
| SA-0371 | analyze_bacterial_growth_rate | — | biomni_entries/biomni.tool.synthetic_biology.analyze_bacterial_growth_rate; outside_explicit_current_scope | — |
| SA-0372 | analyze_barcode_sequencing_data | B-L130-analyze_barcode_sequencing_data | biomni_entries/biomni.tool.synthetic_biology.analyze_barcode_sequencing_data; mapped_required_or_scoped_helper | — |
| SA-0373 | analyze_bifurcation_diagram | — | biomni_entries/biomni.tool.synthetic_biology.analyze_bifurcation_diagram; outside_explicit_current_scope | — |
| SA-0374 | create_biochemical_network_sbml_model | — | biomni_entries/biomni.tool.synthetic_biology.create_biochemical_network_sbml_model; outside_explicit_current_scope | — |
| SA-0375 | optimize_codons_for_heterologous_expression | — | biomni_entries/biomni.tool.synthetic_biology.optimize_codons_for_heterologous_expression; outside_explicit_current_scope | — |
| SA-0376 | simulate_gene_circuit_with_growth_feedback | — | biomni_entries/biomni.tool.synthetic_biology.simulate_gene_circuit_with_growth_feedback; outside_explicit_current_scope | — |
| SA-0377 | identify_fas_functional_domains | B-L098-identify_fas_functional_domains | biomni_entries/biomni.tool.synthetic_biology.identify_fas_functional_domains; mapped_required_or_scoped_helper | — |
| SA-0378 | perform_flux_balance_analysis | B-L164-perform_flux_balance_analysis | biomni_entries/biomni.tool.systems_biology.perform_flux_balance_analysis; mapped_required_or_scoped_helper | — |
| SA-0379 | model_protein_dimerization_network | — | biomni_entries/biomni.tool.systems_biology.model_protein_dimerization_network; outside_explicit_current_scope | — |
| SA-0380 | simulate_metabolic_network_perturbation | — | biomni_entries/biomni.tool.systems_biology.simulate_metabolic_network_perturbation; outside_explicit_current_scope | — |
| SA-0381 | simulate_protein_signaling_network | — | biomni_entries/biomni.tool.systems_biology.simulate_protein_signaling_network; outside_explicit_current_scope | — |
| SA-0382 | compare_protein_structures | B-L107-compare_protein_structures | biomni_entries/biomni.tool.systems_biology.compare_protein_structures; mapped_required_or_scoped_helper | — |
| SA-0383 | simulate_renin_angiotensin_system_dynamics | — | biomni_entries/biomni.tool.systems_biology.simulate_renin_angiotensin_system_dynamics; outside_explicit_current_scope | — |
| SA-0384 | query_chatnt | — | biomni_entries/biomni.tool.systems_biology.query_chatnt; excluded_by_current_goal | — |
| SA-0385 | preprocess_image | — | biomni_entries/biomni.tool.bioimaging.preprocess_image; excluded_by_current_goal | — |
| SA-0386 | get_hpo_names | — | biomni_entries/biomni.tool.database.get_hpo_names; outside_explicit_current_scope | — |
| SA-0387 | clear_captured_plots | — | biomni_entries/biomni.tool.support_tools.clear_captured_plots; outside_explicit_current_scope | — |
| SA-0388 | get_captured_plots | — | biomni_entries/biomni.tool.support_tools.get_captured_plots; outside_explicit_current_scope | — |
| SA-0389 | query_alphafold | E-L292-alphafold-protein-structure-database, E-L309-query_alphafold | gentner_owned_entries/gentner_ave.tools.online_queries.query_alphafold; mapped_required_or_scoped_helper | biomni.tool.database.query_alphafold |
| SA-0390 | query_arxiv | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_arxiv; excluded_by_current_goal | — |
| SA-0391 | query_cbioportal | E-L303-cbioportal, E-L309-query_cbioportal | gentner_owned_entries/gentner_ave.tools.online_queries.query_cbioportal; mapped_required_or_scoped_helper | biomni.tool.database.query_cbioportal |
| SA-0392 | query_chembl | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_chembl; outside_explicit_current_scope | biomni.tool.database.query_chembl |
| SA-0393 | query_clinicaltrials | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_clinicaltrials; excluded_by_current_goal | biomni.tool.database.query_clinicaltrials |
| SA-0394 | query_clinvar | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_clinvar; outside_explicit_current_scope | gentner_ave.tools.ncbi.query_ncbi_database |
| SA-0395 | query_dailymed | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_dailymed; outside_explicit_current_scope | biomni.tool.database.query_dailymed |
| SA-0396 | query_dbsnp | E-L298-dbsnp, E-L309-query_dbsnp | gentner_owned_entries/gentner_ave.tools.online_queries.query_dbsnp; mapped_required_or_scoped_helper | gentner_ave.tools.ncbi.query_ncbi_database |
| SA-0397 | query_encode | E-L299-encode, E-L309-query_encode | gentner_owned_entries/gentner_ave.tools.online_queries.query_encode; mapped_required_or_scoped_helper | biomni.tool.database.query_encode |
| SA-0398 | query_ensembl | E-L298-ensembl, E-L309-query_ensembl | gentner_owned_entries/gentner_ave.tools.online_queries.query_ensembl; mapped_required_or_scoped_helper | biomni.tool.database.query_ensembl |
| SA-0399 | query_geo | E-L289-ncbi-geo, E-L309-query_geo | gentner_owned_entries/gentner_ave.tools.online_queries.query_geo; mapped_required_or_scoped_helper | gentner_ave.tools.ncbi.query_ncbi_database |
| SA-0400 | query_gnomad | E-L298-gnomad, E-L309-query_gnomad | gentner_owned_entries/gentner_ave.tools.online_queries.query_gnomad; mapped_required_or_scoped_helper | biomni.tool.database.query_gnomad |
| SA-0401 | query_gwas_catalog | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_gwas_catalog; excluded_by_current_goal | biomni.tool.database.query_gwas_catalog |
| SA-0402 | query_interpro | E-L291-interpro, E-L309-query_interpro | gentner_owned_entries/gentner_ave.tools.online_queries.query_interpro; mapped_required_or_scoped_helper | biomni.tool.database.query_interpro |
| SA-0403 | query_kegg | E-L295-kegg, E-L309-query_kegg | gentner_owned_entries/gentner_ave.tools.online_queries.query_kegg; mapped_required_or_scoped_helper | biomni.tool.database.query_kegg |
| SA-0404 | query_opentarget | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_opentarget; outside_explicit_current_scope | biomni.tool.database.query_opentarget |
| SA-0405 | query_pdb | E-L293-rcsb-pdb, E-L309-query_pdb | gentner_owned_entries/gentner_ave.tools.online_queries.query_pdb; mapped_required_or_scoped_helper | biomni.tool.database.query_pdb |
| SA-0406 | query_pubchem | E-L297-pubchem, E-L309-query_pubchem | gentner_owned_entries/gentner_ave.tools.online_queries.query_pubchem; mapped_required_or_scoped_helper | biomni.tool.database.query_pubchem |
| SA-0407 | query_pubmed | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_pubmed; excluded_by_current_goal | — |
| SA-0408 | query_reactome | E-L295-reactome, E-L309-query_reactome | gentner_owned_entries/gentner_ave.tools.online_queries.query_reactome; mapped_required_or_scoped_helper | biomni.tool.database.query_reactome |
| SA-0409 | query_scholar | — | gentner_owned_entries/gentner_ave.tools.online_queries.query_scholar; excluded_by_current_goal | — |
| SA-0410 | query_stringdb | E-L294-string, E-L309-query_stringdb | gentner_owned_entries/gentner_ave.tools.online_queries.query_stringdb; mapped_required_or_scoped_helper | biomni.tool.database.query_stringdb |
| SA-0411 | query_uniprot | E-L290-uniprot, E-L309-query_uniprot | gentner_owned_entries/gentner_ave.tools.online_queries.query_uniprot; mapped_required_or_scoped_helper | biomni.tool.database.query_uniprot |
| SA-0412 | search_google | — | gentner_owned_entries/gentner_ave.tools.online_queries.search_google; excluded_by_current_goal | — |
| SA-0413 | efetch | E-L311-efetch | gentner_owned_entries/gentner_ave.tools.ncbi.efetch; mapped_required_or_scoped_helper | — |
| SA-0414 | esearch | E-L311-esearch | gentner_owned_entries/gentner_ave.tools.ncbi.esearch; mapped_required_or_scoped_helper | — |
| SA-0415 | esummary | E-L311-esummary | gentner_owned_entries/gentner_ave.tools.ncbi.esummary; mapped_required_or_scoped_helper | — |
| SA-0416 | query_ncbi_database | E-L311-query_ncbi_database | gentner_owned_entries/gentner_ave.tools.ncbi.query_ncbi_database; mapped_required_or_scoped_helper | — |
| SA-0417 | data_lake_one_liners | — | gentner_owned_entries/gentner_ave.tools.data_lake.data_lake_one_liners; outside_explicit_current_scope | — |
| SA-0418 | download_geo_series | B-L176-download_geo_series, E-L289-ncbi-geo | gentner_owned_entries/gentner_ave.tools.data_lake.download_geo_series; mapped_required_or_scoped_helper | — |
| SA-0419 | inspect_file | B-L177-inspect_file | gentner_owned_entries/gentner_ave.tools.data_lake.inspect_file; mapped_required_or_scoped_helper | — |
| SA-0420 | query_arxiv | — | gentner_owned_entries/gentner_ave.tools.literature.query_arxiv; excluded_by_current_goal | — |
| SA-0421 | query_pubmed | — | gentner_owned_entries/gentner_ave.tools.literature.query_pubmed; excluded_by_current_goal | — |
| SA-0422 | query_scholar | — | gentner_owned_entries/gentner_ave.tools.literature.query_scholar; excluded_by_current_goal | — |
| SA-0423 | search_google | — | gentner_owned_entries/gentner_ave.tools.literature.search_google; excluded_by_current_goal | — |
| SA-0424 | get_tool_schema | — | gentner_owned_entries/gentner_ave.tools.biomni_catalog.get_tool_schema; outside_explicit_current_scope | — |
| SA-0425 | list_module_tools | — | gentner_owned_entries/gentner_ave.tools.biomni_catalog.list_module_tools; outside_explicit_current_scope | — |
| SA-0426 | search_libraries | — | gentner_owned_entries/gentner_ave.tools.biomni_catalog.search_libraries; outside_explicit_current_scope | — |
| SA-0427 | run_bash_script | — | gentner_owned_entries/gentner_ave.tools.execution.run_bash_script; outside_explicit_current_scope | — |
| SA-0428 | run_python_subprocess | — | gentner_owned_entries/gentner_ave.tools.execution.run_python_subprocess; outside_explicit_current_scope | — |
| SA-0429 | run_r_code | — | gentner_owned_entries/gentner_ave.tools.execution.run_r_code; outside_explicit_current_scope | — |
| SA-0430 | alphafold-skill | E-L292-alphafold-protein-structure-database | entries/alphafold-skill; mapped_required_or_scoped_helper | — |
| SA-0431 | bgee-skill | E-L301-bgee | entries/bgee-skill; mapped_required_or_scoped_helper | — |
| SA-0432 | bindingdb-skill | — | entries/bindingdb-skill; outside_explicit_current_scope | — |
| SA-0433 | biobankjapan-phewas-skill | — | entries/biobankjapan-phewas-skill; excluded_by_current_goal | — |
| SA-0434 | biorxiv-skill | — | entries/biorxiv-skill; excluded_by_current_goal | — |
| SA-0435 | biostudies-arrayexpress-skill | E-L300-biostudies-arrayexpress | entries/biostudies-arrayexpress-skill; mapped_required_or_scoped_helper | — |
| SA-0436 | cbioportal-skill | E-L303-cbioportal | entries/cbioportal-skill; mapped_required_or_scoped_helper | — |
| SA-0437 | cellxgene-skill | E-L302-cellxgene | entries/cellxgene-skill; mapped_required_or_scoped_helper | — |
| SA-0438 | chebi-skill | E-L297-chebi | entries/chebi-skill; mapped_required_or_scoped_helper | — |
| SA-0439 | chembl-skill | — | entries/chembl-skill; outside_explicit_current_scope | — |
| SA-0440 | civic-skill | — | entries/civic-skill; outside_explicit_current_scope | — |
| SA-0441 | clinicaltrials-skill | — | entries/clinicaltrials-skill; excluded_by_current_goal | — |
| SA-0442 | clinvar-variation-skill | E-L298-dbsnp | entries/clinvar-variation-skill; mapped_required_or_scoped_helper | — |
| SA-0443 | efo-ontology-skill | — | entries/efo-ontology-skill; outside_explicit_current_scope | — |
| SA-0444 | encode-skill | E-L299-encode | entries/encode-skill; mapped_required_or_scoped_helper | — |
| SA-0445 | ensembl-skill | E-L298-ensembl | entries/ensembl-skill; mapped_required_or_scoped_helper | — |
| SA-0446 | epigraphdb-skill | — | entries/epigraphdb-skill; outside_explicit_current_scope | — |
| SA-0447 | eqtl-catalogue-skill | E-L301-eqtl-catalogue | entries/eqtl-catalogue-skill; mapped_required_or_scoped_helper | — |
| SA-0448 | eva-skill | E-L298-eva | entries/eva-skill; mapped_required_or_scoped_helper | — |
| SA-0449 | finngen-phewas-skill | — | entries/finngen-phewas-skill; excluded_by_current_goal | — |
| SA-0450 | genebass-gene-burden-skill | — | entries/genebass-gene-burden-skill; outside_explicit_current_scope | — |
| SA-0451 | gnomad-graphql-skill | E-L298-gnomad | entries/gnomad-graphql-skill; mapped_required_or_scoped_helper | — |
| SA-0452 | gtex-eqtl-skill | E-L301-gtex | entries/gtex-eqtl-skill; mapped_required_or_scoped_helper | — |
| SA-0453 | gwas-catalog-skill | — | entries/gwas-catalog-skill; excluded_by_current_goal | — |
| SA-0454 | hmdb-skill | E-L297-hmdb | entries/hmdb-skill; mapped_required_or_scoped_helper | — |
| SA-0455 | human-protein-atlas-skill | E-L301-human-protein-atlas | entries/human-protein-atlas-skill; mapped_required_or_scoped_helper | — |
| SA-0456 | ipd-skill | — | entries/ipd-skill; outside_explicit_current_scope | — |
| SA-0457 | locus-to-gene-mapper-skill | — | entries/locus-to-gene-mapper-skill; outside_explicit_current_scope | — |
| SA-0458 | metabolights-skill | E-L305-metabolights | entries/metabolights-skill; mapped_required_or_scoped_helper | — |
| SA-0459 | mgnify-skill | E-L306-mgnify | entries/mgnify-skill; mapped_required_or_scoped_helper | — |
| SA-0460 | ncbi-blast-skill | E-L287-ncbi-blast | entries/ncbi-blast-skill; mapped_required_or_scoped_helper | — |
| SA-0461 | ncbi-clinicaltables-skill | E-L288-ncbi-gene | entries/ncbi-clinicaltables-skill; mapped_required_or_scoped_helper | — |
| SA-0462 | ncbi-datasets-skill | E-L288-ncbi-datasets | entries/ncbi-datasets-skill; mapped_required_or_scoped_helper | — |
| SA-0463 | ncbi-entrez-skill | E-L288-ncbi-assembly, E-L288-ncbi-gene, E-L288-ncbi-nucleotide, E-L288-ncbi-protein, E-L288-ncbi-taxonomy, E-L289-ncbi-geo, E-L289-ncbi-sra | entries/ncbi-entrez-skill; mapped_required_or_scoped_helper | — |
| SA-0464 | ncbi-pmc-skill | — | entries/ncbi-pmc-skill; excluded_by_current_goal | — |
| SA-0465 | opentargets-skill | — | entries/opentargets-skill; outside_explicit_current_scope | — |
| SA-0466 | pharmgkb-skill | — | entries/pharmgkb-skill; outside_explicit_current_scope | — |
| SA-0467 | pride-skill | E-L304-pride | entries/pride-skill; mapped_required_or_scoped_helper | — |
| SA-0468 | proteomexchange-skill | E-L304-proteomexchange | entries/proteomexchange-skill; mapped_required_or_scoped_helper | — |
| SA-0469 | pubchem-pug-skill | E-L297-pubchem | entries/pubchem-pug-skill; mapped_required_or_scoped_helper | — |
| SA-0470 | quickgo-skill | E-L296-quickgo | entries/quickgo-skill; mapped_required_or_scoped_helper | — |
| SA-0471 | rcsb-pdb-skill | E-L293-rcsb-pdb | entries/rcsb-pdb-skill; mapped_required_or_scoped_helper | — |
| SA-0472 | reactome-skill | E-L295-reactome | entries/reactome-skill; mapped_required_or_scoped_helper | — |
| SA-0473 | research-router-skill | — | entries/research-router-skill; outside_explicit_current_scope | — |
| SA-0474 | rhea-skill | E-L295-rhea | entries/rhea-skill; mapped_required_or_scoped_helper | — |
| SA-0475 | rnacentral-skill | — | entries/rnacentral-skill; outside_explicit_current_scope | — |
| SA-0476 | string-skill | E-L294-string | entries/string-skill; mapped_required_or_scoped_helper | — |
| SA-0477 | tpmi-phewas-skill | — | entries/tpmi-phewas-skill; excluded_by_current_goal | — |
| SA-0478 | ukb-topmed-phewas-skill | — | entries/ukb-topmed-phewas-skill; excluded_by_current_goal | — |
| SA-0479 | uniprot-skill | E-L290-uniprot | entries/uniprot-skill; mapped_required_or_scoped_helper | — |
| SA-0480 | cmalign | A-L067-cmalign | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmalign; mapped_required_or_scoped_helper | — |
| SA-0481 | cmbuild | A-L077-cmbuild | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmbuild; mapped_required_or_scoped_helper | — |
| SA-0482 | cmcalibrate | A-L077-cmcalibrate | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmcalibrate; mapped_required_or_scoped_helper | — |
| SA-0483 | cmconvert | A-L077-cmconvert | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmconvert; mapped_required_or_scoped_helper | — |
| SA-0484 | cmemit | A-L077-cmemit | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmemit; mapped_required_or_scoped_helper | — |
| SA-0485 | cmfetch | A-L077-cmfetch | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmfetch; mapped_required_or_scoped_helper | — |
| SA-0486 | cmpress | A-L077-cmpress | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmpress; mapped_required_or_scoped_helper | — |
| SA-0487 | cmscan | A-L067-cmscan | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmscan; mapped_required_or_scoped_helper | — |
| SA-0488 | cmsearch | A-L067-cmsearch | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmsearch; mapped_required_or_scoped_helper | — |
| SA-0489 | cmstat | A-L077-cmstat | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5-install/bin/cmstat; mapped_required_or_scoped_helper | — |
| SA-0490 | blast_formatter | A-L078-blast_formatter | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blast_formatter; mapped_required_or_scoped_helper | — |
| SA-0491 | blast_formatter_vdb | A-L078-blast_formatter_vdb | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blast_formatter_vdb; mapped_required_or_scoped_helper | — |
| SA-0492 | blast_vdb_cmd | A-L078-blast_vdb_cmd | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blast_vdb_cmd; mapped_required_or_scoped_helper | — |
| SA-0493 | blastdb_aliastool | A-L078-blastdb_aliastool | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blastdb_aliastool; mapped_required_or_scoped_helper | — |
| SA-0494 | blastdbcheck | A-L078-blastdbcheck | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blastdbcheck; mapped_required_or_scoped_helper | — |
| SA-0495 | blastdbcmd | A-L078-blastdbcmd | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blastdbcmd; mapped_required_or_scoped_helper | — |
| SA-0496 | blastn | A-L069-blastn-database, A-L069-blastn-pairwise | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blastn; mapped_required_or_scoped_helper | — |
| SA-0497 | blastn_vdb | A-L070-blastn_vdb-database | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blastn_vdb; mapped_required_or_scoped_helper | — |
| SA-0498 | blastp | A-L069-blastp-database, A-L069-blastp-pairwise | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blastp; mapped_required_or_scoped_helper | — |
| SA-0499 | blastx | A-L069-blastx-database, A-L069-blastx-pairwise | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/blastx; mapped_required_or_scoped_helper | — |
| SA-0500 | convert2blastmask | A-L078-convert2blastmask | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/convert2blastmask; mapped_required_or_scoped_helper | — |
| SA-0501 | deltablast | A-L070-deltablast-database | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/deltablast; mapped_required_or_scoped_helper | — |
| SA-0502 | dustmasker | A-L078-dustmasker | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/dustmasker; mapped_required_or_scoped_helper | — |
| SA-0503 | makeblastdb | A-L078-makeblastdb | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/makeblastdb; mapped_required_or_scoped_helper | — |
| SA-0504 | makembindex | A-L078-makembindex | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/makembindex; mapped_required_or_scoped_helper | — |
| SA-0505 | makeprofiledb | A-L078-makeprofiledb | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/makeprofiledb; mapped_required_or_scoped_helper | — |
| SA-0506 | psiblast | A-L070-psiblast-database | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/psiblast; mapped_required_or_scoped_helper | — |
| SA-0507 | rpsblast | A-L070-rpsblast-database | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/rpsblast; mapped_required_or_scoped_helper | — |
| SA-0508 | rpstblastn | A-L070-rpstblastn-database | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/rpstblastn; mapped_required_or_scoped_helper | — |
| SA-0509 | segmasker | A-L078-segmasker | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/segmasker; mapped_required_or_scoped_helper | — |
| SA-0510 | tblastn | A-L069-tblastn-database, A-L069-tblastn-pairwise | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/tblastn; mapped_required_or_scoped_helper | — |
| SA-0511 | tblastn_vdb | A-L070-tblastn_vdb-database | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/tblastn_vdb; mapped_required_or_scoped_helper | — |
| SA-0512 | tblastx | A-L069-tblastx-database, A-L069-tblastx-pairwise | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/tblastx; mapped_required_or_scoped_helper | — |
| SA-0513 | windowmasker | A-L078-windowmasker | deployment/local/binary_directory_facts/resources/software/ncbi-blast-2.17.0+/bin/windowmasker; mapped_required_or_scoped_helper | — |
| SA-0514 | alimask | A-L076-alimask | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/alimask; mapped_required_or_scoped_helper | — |
| SA-0515 | build_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/build_utest; supporting_source_only | — |
| SA-0516 | generic_fwdback_chk_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/generic_fwdback_chk_utest; supporting_source_only | — |
| SA-0517 | generic_fwdback_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/generic_fwdback_utest; supporting_source_only | — |
| SA-0518 | generic_msv_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/generic_msv_utest; supporting_source_only | — |
| SA-0519 | generic_stotrace_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/generic_stotrace_utest; supporting_source_only | — |
| SA-0520 | generic_viterbi_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/generic_viterbi_utest; supporting_source_only | — |
| SA-0521 | hmmalign | A-L066-hmmalign | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmalign; mapped_required_or_scoped_helper | — |
| SA-0522 | hmmbuild | A-L076-hmmbuild | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmbuild; mapped_required_or_scoped_helper | — |
| SA-0523 | hmmc2 | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmc2; supporting_source_only | — |
| SA-0524 | hmmconvert | A-L076-hmmconvert | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmconvert; mapped_required_or_scoped_helper | — |
| SA-0525 | hmmd_search_status_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmd_search_status_utest; supporting_source_only | — |
| SA-0526 | hmmemit | A-L076-hmmemit | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmemit; mapped_required_or_scoped_helper | — |
| SA-0527 | hmmer_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmer_utest; supporting_source_only | — |
| SA-0528 | hmmerfm-exactmatch | A-L076-hmmerfm-exactmatch | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmerfm-exactmatch; mapped_required_or_scoped_helper | — |
| SA-0529 | hmmfetch | A-L076-hmmfetch | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmfetch; mapped_required_or_scoped_helper | — |
| SA-0530 | hmmlogo | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmlogo; outside_explicit_current_scope | — |
| SA-0531 | hmmpgmd | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmpgmd; supporting_source_only | — |
| SA-0532 | hmmpgmd2msa_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmpgmd2msa_utest; supporting_source_only | — |
| SA-0533 | hmmpgmd_shard | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmpgmd_shard; supporting_source_only | — |
| SA-0534 | hmmpress | A-L076-hmmpress | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmpress; mapped_required_or_scoped_helper | — |
| SA-0535 | hmmscan | A-L065-hmmscan | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmscan; mapped_required_or_scoped_helper | — |
| SA-0536 | hmmsearch | A-L065-hmmsearch | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmsearch; mapped_required_or_scoped_helper | — |
| SA-0537 | hmmsim | A-L076-hmmsim | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmsim; mapped_required_or_scoped_helper | — |
| SA-0538 | hmmstat | A-L076-hmmstat | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/hmmstat; mapped_required_or_scoped_helper | — |
| SA-0539 | itest_brute | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/itest_brute; supporting_source_only | — |
| SA-0540 | jackhmmer | A-L065-jackhmmer | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/jackhmmer; mapped_required_or_scoped_helper | — |
| SA-0541 | logsum_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/logsum_utest; supporting_source_only | — |
| SA-0542 | makehmmerdb | A-L076-makehmmerdb | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/makehmmerdb; mapped_required_or_scoped_helper | — |
| SA-0543 | modelconfig_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/modelconfig_utest; supporting_source_only | — |
| SA-0544 | nhmmer | A-L065-nhmmer | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/nhmmer; mapped_required_or_scoped_helper | — |
| SA-0545 | nhmmscan | A-L065-nhmmscan | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/nhmmscan; mapped_required_or_scoped_helper | — |
| SA-0546 | p7_alidisplay_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_alidisplay_utest; supporting_source_only | — |
| SA-0547 | p7_bg_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_bg_utest; supporting_source_only | — |
| SA-0548 | p7_domain_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_domain_utest; supporting_source_only | — |
| SA-0549 | p7_gmx_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_gmx_utest; supporting_source_only | — |
| SA-0550 | p7_gmxchk_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_gmxchk_utest; supporting_source_only | — |
| SA-0551 | p7_hit_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_hit_utest; supporting_source_only | — |
| SA-0552 | p7_hmm_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_hmm_utest; supporting_source_only | — |
| SA-0553 | p7_hmmd_search_stats_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_hmmd_search_stats_utest; supporting_source_only | — |
| SA-0554 | p7_hmmfile_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_hmmfile_utest; supporting_source_only | — |
| SA-0555 | p7_profile_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_profile_utest; supporting_source_only | — |
| SA-0556 | p7_scoredata_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_scoredata_utest; supporting_source_only | — |
| SA-0557 | p7_tophits_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_tophits_utest; supporting_source_only | — |
| SA-0558 | p7_trace_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/p7_trace_utest; supporting_source_only | — |
| SA-0559 | phmmer | A-L065-phmmer | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/phmmer; mapped_required_or_scoped_helper | — |
| SA-0560 | seqmodel_utest | — | deployment/local/binary_directory_facts/resources/software/infernal-1.1.5/hmmer/src/seqmodel_utest; supporting_source_only | — |
| SA-0561 | antibiotics | — | collection_prompt_definitions/antibiotics; outside_explicit_current_scope | — |
| SA-0562 | bioset | D-L270-bioset | collection_prompt_definitions/bioset; mapped_required_or_scoped_helper | — |
| SA-0563 | bioset_result | D-L271-bioset_result | collection_prompt_definitions/bioset_result; mapped_required_or_scoped_helper | — |
| SA-0564 | enzyme_class_ref | D-L261-enzyme_class_ref | collection_prompt_definitions/enzyme_class_ref; mapped_required_or_scoped_helper | — |
| SA-0565 | epitope | — | collection_prompt_definitions/epitope; outside_explicit_current_scope | — |
| SA-0566 | epitope_assay | — | collection_prompt_definitions/epitope_assay; outside_explicit_current_scope | — |
| SA-0567 | experiment | D-L269-experiment | collection_prompt_definitions/experiment; mapped_required_or_scoped_helper | — |
| SA-0568 | gene_ontology_ref | D-L262-gene_ontology_ref | collection_prompt_definitions/gene_ontology_ref; mapped_required_or_scoped_helper | — |
| SA-0569 | genome | D-L240-genome | collection_prompt_definitions/genome; mapped_required_or_scoped_helper | — |
| SA-0570 | genome_amr | — | collection_prompt_definitions/genome_amr; outside_explicit_current_scope | — |
| SA-0571 | genome_feature | D-L241-genome_feature | collection_prompt_definitions/genome_feature; mapped_required_or_scoped_helper | — |
| SA-0572 | genome_sequence | D-L242-genome_sequence | collection_prompt_definitions/genome_sequence; mapped_required_or_scoped_helper | — |
| SA-0573 | id_ref | D-L253-id_ref | collection_prompt_definitions/id_ref; mapped_required_or_scoped_helper | — |
| SA-0574 | misc_niaid_sgc | — | collection_prompt_definitions/misc_niaid_sgc; outside_explicit_current_scope | — |
| SA-0575 | pathway | D-L257-pathway | collection_prompt_definitions/pathway; mapped_required_or_scoped_helper | — |
| SA-0576 | pathway_ref | D-L258-pathway_ref | collection_prompt_definitions/pathway_ref; mapped_required_or_scoped_helper | — |
| SA-0577 | ppi | D-L266-ppi | collection_prompt_definitions/ppi; mapped_required_or_scoped_helper | — |
| SA-0578 | protein_family_ref | D-L246-protein_family_ref | collection_prompt_definitions/protein_family_ref; mapped_required_or_scoped_helper | — |
| SA-0579 | protein_feature | D-L247-protein_feature | collection_prompt_definitions/protein_feature; mapped_required_or_scoped_helper | — |
| SA-0580 | protein_structure | D-L265-protein_structure | collection_prompt_definitions/protein_structure; mapped_required_or_scoped_helper | — |
| SA-0581 | sequence_feature | D-L248-sequence_feature | collection_prompt_definitions/sequence_feature; mapped_required_or_scoped_helper | — |
| SA-0582 | sequence_feature_vt | D-L249-sequence_feature_vt | collection_prompt_definitions/sequence_feature_vt; mapped_required_or_scoped_helper | — |
| SA-0583 | serology | — | collection_prompt_definitions/serology; outside_explicit_current_scope | — |
| SA-0584 | sp_gene | — | collection_prompt_definitions/sp_gene; outside_explicit_current_scope | — |
| SA-0585 | sp_gene_ref | — | collection_prompt_definitions/sp_gene_ref; outside_explicit_current_scope | — |
| SA-0586 | spike_lineage | — | collection_prompt_definitions/spike_lineage; outside_explicit_current_scope | — |
| SA-0587 | spike_variant | — | collection_prompt_definitions/spike_variant; outside_explicit_current_scope | — |
| SA-0588 | strain | — | collection_prompt_definitions/strain; outside_explicit_current_scope | — |
| SA-0589 | structured_assertion | D-L250-structured_assertion | collection_prompt_definitions/structured_assertion; mapped_required_or_scoped_helper | — |
| SA-0590 | subsystem | D-L259-subsystem | collection_prompt_definitions/subsystem; mapped_required_or_scoped_helper | — |
| SA-0591 | subsystem_ref | D-L260-subsystem_ref | collection_prompt_definitions/subsystem_ref; mapped_required_or_scoped_helper | — |
| SA-0592 | surveillance | — | collection_prompt_definitions/surveillance; outside_explicit_current_scope | — |
| SA-0593 | taxonomy | D-L254-taxonomy | collection_prompt_definitions/taxonomy; mapped_required_or_scoped_helper | — |
| SA-0594 | sequence_composition | A-L059-reads, A-L059-sequence | groups/sequence_composition; mapped_required_or_scoped_helper | — |
| SA-0595 | sequence_translation | A-L060-translation | groups/sequence_translation; mapped_required_or_scoped_helper | — |
| SA-0596 | sequence_views | A-L060-extraction, A-L060-translation | groups/sequence_views; mapped_required_or_scoped_helper | — |
| SA-0597 | biopython_pairwise | A-L061-dna-global, A-L061-dna-local, A-L061-protein-global, A-L061-protein-local, A-L061-rna-global, A-L061-rna-local | groups/biopython_pairwise; mapped_required_or_scoped_helper | — |
| SA-0598 | prodigal | A-L062-metagenomic, A-L062-single-genome | groups/prodigal; mapped_required_or_scoped_helper | — |
| SA-0599 | minimap2 | A-L063-lr-hq, A-L063-map-hifi, A-L063-map-iclr, A-L063-map-ont, A-L063-map-pb, A-L063-sr | groups/minimap2; mapped_required_or_scoped_helper | — |
| SA-0600 | infernal_cmsearch | A-L067-cmsearch | groups/infernal_cmsearch; mapped_required_or_scoped_helper | — |
| SA-0601 | alignment_site_readers | A-L064-blast-hsp, A-L064-mapping-correspondence, A-L064-native-pairwise | groups/alignment_site_readers; mapped_required_or_scoped_helper | — |
| SA-0602 | genbank_neighborhood | E-L288-ncbi-nucleotide | groups/genbank_neighborhood; mapped_required_or_scoped_helper | — |
| SA-0603 | rfam_batch | A-L068-rfam-batch | groups/rfam_batch; mapped_required_or_scoped_helper | — |
| SA-0604 | rfam_model | E-L291-rfam | groups/rfam_model; mapped_required_or_scoped_helper | — |
| SA-0605 | blast | A-L069-blastn-database, A-L069-blastp-database, A-L069-blastx-database, A-L069-tblastn-database, A-L069-tblastx-database, E-L287-ncbi-blast | groups/blast; mapped_required_or_scoped_helper | — |
| SA-0606 | uniprot | E-L290-uniprot | groups/uniprot; mapped_required_or_scoped_helper | — |
| SA-0607 | ncbi_data | E-L288-ncbi-assembly, E-L288-ncbi-gene, E-L288-ncbi-nucleotide, E-L288-ncbi-protein, E-L288-ncbi-taxonomy | groups/ncbi_data; mapped_required_or_scoped_helper | — |
| SA-0608 | rhea | E-L295-rhea | groups/rhea; mapped_required_or_scoped_helper | — |
| SA-0609 | chebi | E-L297-chebi | groups/chebi; mapped_required_or_scoped_helper | — |
| SA-0610 | bvbrc_data | D-L240-genome, D-L241-genome_feature, D-L246-protein_family_ref | groups/bvbrc_data; mapped_required_or_scoped_helper | — |
| SA-0611 | hmmer_api | A-L065-hmmscan, A-L065-phmmer | groups/hmmer_api; mapped_required_or_scoped_helper | — |
| SA-0612 | phmmer_local | A-L065-phmmer | groups/phmmer_local; mapped_required_or_scoped_helper | — |
| SA-0613 | material_intake | B-L177-inspect_file | groups/material_intake; mapped_required_or_scoped_helper | — |
| SA-0614 | read_library | A-L059-reads | groups/read_library; mapped_required_or_scoped_helper | — |
| SA-0615 | record_and_source_read | B-L177-inspect_file | groups/record_and_source_read; mapped_required_or_scoped_helper | — |
| SA-0616 | public_job_inventory | — | groups/public_job_inventory; supporting_source_only | — |
| SA-0617 | practical_execution | — | groups/practical_execution; supporting_source_only | — |
| SA-0618 | execution_capability_and_bytes | — | groups/execution_capability_and_bytes; supporting_source_only | — |
| SA-0619 | progress | — | groups/progress; supporting_source_only | — |
| SA-0620 | literature_and_document_exclusions | — | groups/literature_and_document_exclusions; supporting_source_only | — |
| SA-0621 | Prodigal | A-L062-metagenomic, A-L062-single-genome | native_algorithm_families/1; mapped_required_or_scoped_helper | — |
| SA-0622 | Pyrodigal | A-L062-metagenomic, A-L062-single-genome | native_algorithm_families/1; mapped_required_or_scoped_helper | — |
