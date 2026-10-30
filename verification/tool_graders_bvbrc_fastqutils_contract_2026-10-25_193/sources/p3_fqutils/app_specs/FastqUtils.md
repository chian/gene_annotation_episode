
# Application specification: FastqUtils

This is the application specification for service with identifier FastqUtils.

The backend script implementing the application is [App-FastqUtils.pl](../service-scripts/App-FastqUtils.pl).

The raw JSON file for this specification is [FastqUtils.json](FastqUtils.json).

This service performs the following task:   Useful common processing of fastq files

It takes the following parameters:

| id | label | type | required | default value |
| -- | ----- | ---- | :------: | ------------ |
| reference_genome_id | Reference genome ID | string  |  |  |
| paired_end_libs |  | group  |  |  |
| single_end_libs |  | group  |  |  |
| srr_libs |  | group  |  |  |
| output_path | Output Folder | folder  | :heavy_check_mark: |  |
| output_file | File Basename | wsid  | :heavy_check_mark: |  |
| recipe | Recipe | list  | :heavy_check_mark: | ARRAY(0x557d47c9acc0) |

