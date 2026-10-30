
# Application specification: GenomeAlignment

This is the application specification for service with identifier GenomeAlignment.

The backend script implementing the application is [App-GenomeAlignment.pl](../service-scripts/App-GenomeAlignment.pl).

The raw JSON file for this specification is [GenomeAlignment.json](GenomeAlignment.json).

This service performs the following task:   Uses Mauve to perform multiple whole genome alignment with rearrangements.

It takes the following parameters:

| id | label | type | required | default value |
| -- | ----- | ---- | :------: | ------------ |
| genome_ids | Genome IDs to Align | list  | :heavy_check_mark: | ARRAY(0x55a01eacd3c0) |
| recipe | Mauve recipe | enum  |  | progressiveMauve |
| seedWeight | Seed weight for calculating initial anchors. | float  |  |  |
| maxGappedAlignerLength | Maximum number of base pairs to attempt aligning with the gapped aligner. | float  |  |  |
| maxBreakpointDistanceScale | Set the maximum weight scaling by breakpoint distance.  Must be in [0, 1]. Defaults to 0.9. | float  |  |  |
| conservationDistanceScale | Scale conservation distances by this amount.  Must be in [0, 1].  Defaults to 1. | float  |  |  |
| weight | Minimum pairwise LCB score. | float  |  |  |
| minScaledPenalty | Minimum breakpoint penalty after scaling the penalty by expected divergence. | float  |  |  |
| hmmPGoHomologous | Probability of transitioning from the unrelated to the homologous state | float  |  |  |
| hmmPGoUnrelated | Probability of transitioning from the homologous to the unrelated state | float  |  |  |
| output_path | Output Folder | folder  | :heavy_check_mark: |  |
| output_file | File Basename | wsid  | :heavy_check_mark: |  |

