# Scripts for "Machine learning reveals signature of promiscuous microbial amidases for micropollutant biotransformations"

This repository contains the data analysis and figure plotting scripts for the manuscript:

**"Machine learning reveals signature of promiscuous microbial amidases for micropollutant biotransformations"**  
- Authors: Thierry D. Marti, Diana Schweizer, Yaochun Yu, Milo R. Schärer, Silke I. Probst, Serina L. Robinson
- Associated research article is available open access at doi: [10.1021/acsenvironau.4c00066](https://pubs.acs.org/doi/10.1021/acsenvironau.4c00066)
- For questions or inquiries, please contact: serina.robinson[at]eawag.ch

---

## Repository structure

The repository is organized into three main folders:

- **`data/`**: Contains raw and processed datasets imported by the scripts.
- **`scripts/`**: Contains R scripts for data processing, analysis, figure and table generation.
- **`output/`**: Stores the output figures and the gradient boosting model

---

## Quick start

To run the analysis and generate figures, follow these steps:

1. Open the `amidase-paper.Rproj` file in **RStudio**.
2. Open and execute the desired scripts as described below.

## Script execution order to generate the gradient boosting model

#### Plate reader data processing

The following scripts import plate reader data, analyze it, and output spreadsheets containing hits:

- **`4NP_substrates_data_processing.R`**: Processes 4NP substrate data, exports a spreadsheet of the resulting hits, and generates part of Figure S5.
- **`flutamide_nitroacetanilide_data_processing.R`**: Processes flutamide and nitroacetanilide data, exports a spreadsheet of the resulting hits, and generates part of Figure S5.
- **`paracetamol_data_processing.R`**: Processes paracetamol data, exports a spreadsheet of the resulting hits, and generates part of Figure S5.

#### HPLC data processing

- **`HPLC_data_processing_225nm.R`**  
  Analyzes HPLC data at 225 nm and generates `data_225nm.csv`.
- **`HPLC_data_processing_252nm.R`**  
  Analyzes HPLC data at 252 nm and generates `data_252nm.csv` and `hits_252.xlsx`.
- **`HPLC_data_processing_305nm.R`**  
  Analyzes HPLC data at 305 nm and generates `data_225nm.csv` and `hits_305.xlsx`.

#### Combining and analyzing hits

- **`substrate_screening_combine_hits.R`**: Reads hit spreadsheets from plate reader and HPLC data (there were no hits for substrates quantified at 210 and 225nm), processes them further, and outputs a list of 272 enzyme-substrate combinations.

#### Featurization & gradient boosting model building
- **`chemical_featurization.R`**  
  Uses the **ChemmineR** package to featurize the chemical structures. The features `MW_bond` and `MW_ring` were manually calculated (see *Methods*) and added. The output file is `17_chemical_properties_amidase_substrates_MW_ring_MW_bond.xlsx`.
- **`gradient_boosting_model.R`**  
  Reads in the 272 enzyme-substrate combinations, creates amino acid features, and trains a gradient boosting model. Outputs are stored under `output/machine_learning` as an `.RDS` file alongside performance metrics and a spreadsheet containing the 24 important features.



---

## Scripts for Figure & Table generation

The scripts to generate the publication Figures and Tables are named accordingly.

---

## Additional scripts

- **`rmsd_hits.R`**: Calculates the average and standard deviation of RMSD for 16 enzymes based on DALI server outputs.
- **`get_ncbi_accessions.R`**: Retrieves NCBI assembly accessions for downloading genomes from Thomas-White (2018).
- **`convert_seq_5aap.R`**: featurizes amino acids according to according to Atchley et al. (2005), is executed within **`gradient_boosting_model.R`**



