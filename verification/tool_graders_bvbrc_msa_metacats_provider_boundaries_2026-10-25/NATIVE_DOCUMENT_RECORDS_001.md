# Exact reused native document records

This is an explicit record annex to `PROVIDER_RECORDS_001.md`, transcribed from the actual installed validators on 2026-10-25. It introduces no native parser schema changes. Shared `Artifact`, `Location`, `NativeNumber`, closed-record conventions and completeness values are defined in that document. All native token strings permit blanks unless their original validator requires a nonempty ID. Failed tokens stay represented; row indices preserve original physical data-row ordinals.

```text
MSAFrequencyTable = {table_id:id,artifact:Artifact,alphabet:dna|protein,
 layout:current_without_reference|current_with_reference,encoding:ascii|utf-8,
 header_tokens:[text],completeness:Completeness,rows:[MSAFrequencyRow]}
MSAFrequencyRow = {row_index:index,source_location:Location,
 alignment_position:NativeNumber,reference_position:NativeNumber|null,
 reference_character:text|null,score:NativeNumber,consensus_token:text,
 n_sequences:NativeNumber,dna_counts:DNACounts|null,protein_detail:[ProteinCount]|null}
DNACounts = {A:NativeNumber,T:NativeNumber,G:NativeNumber,C:NativeNumber,
 Deletion:NativeNumber}
ProteinCount = {raw_token:text,raw_residue_token:text,symbol:text|null,count:NativeNumber}
```

Exact DNA header without reference is `Position in Alignment`, `Score`, `Consensus`, `A`, `T`, `G`, `C`, `Deletion`, `Number of Sequences`; protein replaces A/T/G/C/Deletion with `Detail`. Reference layout inserts `Position in Reference` after alignment position and `Reference Character` after Score. Alignment/reference positions require positive integral available values; count fields nonnegative integral; Score nonnegative. Protein `symbol` uses the installed exact native abbreviation map and is null for an unrecognized token; a malformed detail fragment is retained. Table ID is `document_id('msa_frequency_table',artifact,parameters={alphabet,layout,encoding})` using keyword arguments as installed. This table has no per-member SNP identity.

```text
MetaCATSChiSquareTable = {table_id:id,artifact:Artifact,
 layout:current_filtered_tsv|legacy_example_tsv,category_id:id,encoding:ascii|utf-8,
 completeness:Completeness,header_tokens:[text],group_heading_tokens:[text],
 rows:[MetaCATSChiSquareRow]}
MetaCATSChiSquareRow = {row_index:index,source_location:Location,
 position_token:text,position_1based:positive|null,
 position_qualification:plain|legacy_star|invalid,
 chi_square:NativeNumber,p_value:NativeNumber,df:NativeNumber,
 fewer_5_token:text|null,group_cells:[ExportGroupCell]}
ExportGroupCell = {heading_index:index,raw_token:text,symbol_counts:[SymbolCount]}
SymbolCount = {symbol:one-character-string,count:NativeNumber}
MetaCATSPairTable = {table_id:id,artifact:Artifact,layout:'current_filtered_tsv',
 category_id:id,encoding:ascii|utf-8,completeness:Completeness,header_tokens:[text],
 rows:[MetaCATSPairRow]}
MetaCATSPairRow = {row_index:index,source_location:Location,position:NativeNumber,
 p_value:NativeNumber,raw_groups_token:text}
MetaCATSRawRTable = {table_id:id,artifact:Artifact,
 layout:'r_write_table_single_result_string',kind:omnibus|pairwise,category_id:id,
 encoding:ascii|utf-8,completeness:Completeness,wrapper_column_token:text,
 wrapper_row_token:text,section_heading_token:text,
 omnibus_rows:[RawROmnibusRow]|null,pair_rows:[RawRPairRow]|null}
RawROmnibusRow = {row_index:index,source_location:Location,site_token:text,
 position:NativeNumber,chi_square:NativeNumber,p_value:NativeNumber,df:NativeNumber,
 fewer_5_token:text,residue_diversity_token:text,positional_groups:[RawRGroupCell]}
RawRGroupCell = {position_1based:positive,raw_token:text,symbol_counts:[SymbolCount]}
RawRPairRow = {row_index:index,source_location:Location,site_token:text,
 position:NativeNumber,p_value:NativeNumber,column_a_1based:NativeNumber,
 column_b_1based:NativeNumber}
MetadataDocument = {document_id:id,artifact:Artifact,encoding:ascii|utf-8,
 delimiter:'tab',header:present|absent,header_tokens:[text]|null,
 completeness:Completeness,rows:[MetadataRow]}
MetadataRow = {row_index:index,source_location:Location,cells:[text]}
AdjustedMatrix = {document_id:id,artifact:Artifact,category_id:id,
 encoding:ascii|utf-8,completeness:Completeness,rows:[AdjustedMatrixRow]}
AdjustedMatrixRow = {row_index:index,source_location:Location,
 native_member_token:text,native_group_token:text,symbols:[text]}
```

Exact current chi-square prefix is `Position`, `Chi-square_value`, `P-value`, `Degrees_of_freedom`, `Fewer_5`; legacy is `Position`, `Chi-square Value`, `P-value`, `Degree Freedom`. The remaining heading tokens are retained in order, including empty headings. Raw R wraps one result string with the exact quoted column token `"resultCST"` or `"resultMC"`, quoted row token `"1"`, and the native section heading. Only the active raw-R row array is nonnull. Raw R group numbers and pair columns are positional, not biological group names. Native p tokens require exact decimal bounds [0,1]; chi-square nonnegative; df nonnegative integral; positions/columns positive integral. `0` is a native value, `NA` is native_na missing, a tiny nonzero token underflowing binary64 stays underflow, and incompatible values stay qualified.

All five MetaCATS document IDs use existing `document_id` kinds `metacats_chisq_table`, `metacats_pair_table`, `metacats_raw_r_table`, `metacats_metadata`, `metacats_adjusted_matrix` and the exact parser-declaration parameter fields shown in their installed validators. Metadata blank cells and duplicate IDs are retained; complete metadata has consistent widths. Adjusted matrices preserve original token widths on partial input; complete matrices require single-character nonspace symbols and consistent row widths. A `#` is a real retained symbol. It does not encode its own provenance.

```text
TreeDocument = {document_id:id,artifact:Artifact,format:'newick',
 dialect:newick|raxml_branch_labels|bvbrc_double_quoted_names,
 completeness:Completeness,trees:[TreeRecord]}
TreeRecord = {tree_id:id,document_id:id,tree_index:index,
 source_format:newick|phyloxml,root_node_index:0,
 native_rooted_marker:rooted|unrooted|unspecified,nodes:[TreeNode],
 source_location:Location}
TreeNode = {node_index:index,parent_index:index|null,child_indices:[index],
 raw_label:text|null,decoded_label:text|null,label_token:text|null,
 branch_length:number|null,branch_length_token:text|null,
 comments:[TreeComment],source_location:Location}
TreeComment = {text:text,token:text,
 position:before_label|after_label|after_length|before_tree|after_tree,
 location:Location}
```

The new provider only selects the Newick reader in this boundary. The existing TreeRecord validator also accepts phyloxml for other tools; that does not add a phyloxml ReaderSpec here. Newick document IDs are `raw_artifact_ref+'#tree_document'`; tree IDs append `/tree/<original source tree index>`. Node indices are connected preorder indices, never labels. Negative native branch lengths are preserved; labels, quoted text, comments and numeric tokens retain their source locations. Duplicate labels do not create unique tip-to-input joins. Internal labels do not declare support method/scale by themselves. The provider checks envelope equality and per-tree artifact/document associations; it does not call a nonexistent tree-document validator.
