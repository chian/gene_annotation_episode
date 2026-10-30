# SRA Import Service

## Overview

The SRA Import Service enables users to seamlessly integrate sequencing data from the NCBI Sequence Read Archive (SRA) into the BV-BRC platform. This service streamlines the process of retrieving both raw sequencing reads and associated metadata, making it easier for researchers to analyze and contextualize publicly available data.  

## SRA Data Structure

The SRA database organizes sequencing data into a hierarchical structure:

- **Study (SRP accession, previously known as DRP):** A study represents a research project and can include multiple samples.
- **Sample (SRS accession):** A sample refers to a biological specimen and can be associated with multiple experiments.
- **Experiment (SRX accession):** An experiment represents a specific set of conditions applied to a sample and can involve multiple sequencing runs.
- **Run (SRR accession):** A run corresponds to a single sequencing event, typically producing one or more FASTQ files.

## Service Inputs

The service accepts a single primary input:

*   **SRA Accession:**  Users can provide any of the following SRA accession types to initiate data import:
    *   **SRX (Experiment accession):** This option retrieves all runs associated with a specific experiment.
    *   **SRP (Study accession):** This option retrieves all runs associated with a given study.
    *   **SRR (Run accession):** This option retrieves data for a single sequencing run.

## Service Outputs

The service generates two primary outputs:

**1. FASTQ Files:**

*   The service downloads the raw sequencing reads in FASTQ format, maintaining the original file organization from the SRA. For paired-end sequencing data, two separate files (typically denoted with `_1` and `_2` suffixes) are generated, representing each end of the DNA fragments. Files can be downloaded in either compressed (.gz) or uncompressed format.

**2. Metadata File (for SRX and SRP accessions):**

*   For experiment (SRX) and study (SRP) accessions, the service generates a comprehensive metadata file in JSON format. This file captures relevant information about the experiment or study, organized into the following categories:

    *   **Sample Metadata:**
        *   `run_accession`: The unique identifier for the sequencing run.
        *   `experiment_accession`: The identifier for the experiment the run belongs to.
        *   `study_accession`: The identifier for the study the run belongs to.
        *   `sample_name`: The name of the biological sample.
        *   `organism_name`: The scientific name of the organism the sample originates from.
        *   `tax_id`: The NCBI Taxonomy ID for the organism.
        *   `sample_attribute`: Additional attributes describing the sample, such as tissue type, collection date, or other relevant information. 
    *   **Experimental Design:**
        *   `library_strategy`: The sequencing library preparation strategy used (e.g., RNA-Seq, WGS).
        *   `description`:  A free-text description of the experiment.
    *   **Sequencing Information:**
        *   `platform`: The sequencing platform used (e.g., Illumina, PacBio).
        *   `model`: The specific sequencing instrument model.
        *   `library_layout`: The library layout, indicating whether it is single-end or paired-end sequencing.

This metadata file is structured to conform to the requirements of downstream BV-BRC services, particularly the RNA-Seq service, ensuring a smooth transition for further analysis.

**Note:** For single run accessions (SRR), only FASTQ files are generated. Experiment-level metadata is not available for individual runs.

## Scripts and Utilities

The core functionality of the SRA Import Service is implemented in the following Python script:

| Script Name                                | Purpose                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [sra_tools.py](lib/sra_tools.py) | This script handles the retrieval of both FASTQ files and metadata from the SRA database. It employs the NCBI SRA Toolkit to download sequencing reads using the `fasterq-dump` utility, which was chosen as a replacement for the older `fastq-dump` tool due to its improved performance and multi-threading capabilities. The script then processes the retrieved metadata to generate a JSON file compatible with BV-BRC services. Key functions include: <br> * `get_run_info()`: Fetches run information from the SRA given an accession. <br> * `download_fastq()`: Downloads the FASTQ files for the specified run accession. <br> * `process_sra_metadata()`: Parses and structures SRA metadata into a JSON format suitable for downstream analysis within the BV-BRC platform. |

## Additional Resources

- **SRA Metadata Access:** The SRA provides various ways to programmatically access metadata, including:
   - **Web API:**  [https://www.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?](https://www.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?)
   - **SQL Database:**  Metadata can be queried using SQL through the NCBI Entrez system.

- **Example Commands:**

   - Retrieve run information for a study:
     ```bash
     curl 'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=runinfo&term=SRP039561' 
     ```

- **External Tools and Resources:**
   - [EdwardsLab SRA Metadata](https://edwards.sdsu.edu/research/sra-metadata/): Provides insights and scripts for working with SRA metadata. 


## See Also

*   [SRA Import Service](https://bv-brc.org/app/SRAImport) (Link to the service on the BV-BRC website, if available)

## References

*   [SRA Toolkit](https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?view=software)
*   [fasterq-dump](https://github.com/ncbi/sra-tools/wiki/HowTo:-fasterq-dump)
*   [p3diffexp](https://github.com/PATRIC3/p3diffexp)

