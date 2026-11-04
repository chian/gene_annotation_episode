#clear workspace
rm(list = ls())
#load required packages
library(pacman)
pacman::p_load("tidyverse", "readxl", "janitor", "rentrez")
#Get strain IDs from supplementary data 1 in Thomas-White (2018) (doi: 10.1038/s41467-018-03968-5) paper
metadat <- readxl::read_excel("data/thomas_white_metadata/thomas_white_supplementary_data_1.xlsx") %>%
  janitor::clean_names() %>%
  drop_na(species)
#Load table with NCBI assembly accessions of strains
ncbi_acc <- read_excel("data/thomas_white_metadata/thomas_white_bvbrc.xlsx") %>%
  janitor::clean_names() %>%
  dplyr::mutate(strain = stringr::str_to_upper(strain))
#Filter table to contain only strains from Thomas-White (2018) paper
selected <- ncbi_acc %>%
  dplyr::filter(strain %in% metadat$strain_collection_id)
#Output table of NCBI assembly accessions for download
out_list <- selected %>%
  dplyr::select(assembly_accession) %>%
  dplyr::distinct()
readr::write_csv(out_list, "data/thomas_white_metadata/PRJNA316969_accession.csv")
