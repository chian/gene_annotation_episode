library(readr)
library(tidyverse)
library(openxlsx)

# read in the enzyme-host information
dat <- read.xlsx("data/AS_library.xlsx") %>%
  select(p_notation,names) %>%
  separate(names, into = c("accession_number", "host"), sep = "_", extra = "merge", remove = FALSE) %>%
  mutate(host = gsub("_", " ", host)) %>%
  select(-names) %>%
  mutate(host = sub("([a-zA-Z]+ [a-zA-Z]+).*", "\\1", host))

# correct the naming of three enzymes
dat$p_notation[1] <- "p204"
dat$p_notation[2] <- "p203"
dat$p_notation[40] <- "p205"
dat$host[1] <- "Gordonia terrae"
dat$host[2] <- "Corynebacterium aurimucosum"
dat$host[40] <- "Lacticaseibacillus rhamnosus"
dat$p_notation <- toupper(dat$p_notation)

# write as spreadsheet
output_file <- "output/Table_SI_p_notation.xlsx" 
write.xlsx(dat, output_file, rowNames = FALSE)