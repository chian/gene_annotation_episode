
# Application specification: MetaCATS

This is the application specification for service with identifier MetaCATS.

The backend script implementing the application is [App-MetaCATS.pl](../service-scripts/App-MetaCATS.pl).

The raw JSON file for this specification is [MetaCATS.json](MetaCATS.json).

This service performs the following task:   The meta-CATS tool looks for positions that significantly differ between user-defined groups of sequences.

It takes the following parameters:

| id | label | type | required | default value |
| -- | ----- | ---- | :------: | ------------ |
| output_path | Output Folder | folder  | :heavy_check_mark: |  |
| output_file | File Basename | wsid  | :heavy_check_mark: |  |
| p_value | The p-value cutoff. | float  | :heavy_check_mark: | 0.05 |
| year_ranges | The year ranges field. | string  |  |  |
| metadata_group | The metadata type. | string  |  |  |
| input_type | The input type. | enum  | :heavy_check_mark: |  |
| alphabet | sequence alphabet | enum  | :heavy_check_mark: | na |
| groups | Feature groups | list  |  | ARRAY(0x561516b55a88) |
| alignment_file | The alignment file. | WS: feature_protein_fasta  |  |  |
| group_file | The group file. | WS: tsv  |  |  |
| alignment_type | The type of alignment. | enum  |  |  |
| auto_groups |  | group  |  |  |

