# Load required packages
pacman::p_load(
  "tidyverse",
  "ggtree",
  "DECIPHER",
  "treeio",
  "phytools",
  "ape",
  "stringr",
  "RColorBrewer",
  "magrittr",
  "readxl",
  "Biostrings"
)

# Read and root the phylogenetic tree
tr1 <- read.tree("data/trees/20230531_homologs_controls_unique_aligned.fasta.treefile")
midtr <- midpoint.root(tr1)
ggtreem <- ggtree(midtr, color = "gray40", layout = "circular", size = 0.5)

# Read and process metadata for homologs
meta_all <- read.csv("data/trees/20230515_metadata_376_amidases_hit.csv") %>% 
  mutate(label = word(query_name, sep = "_", 3),
         type = "homolog")

# Read and process control sequences
controls <- readAAStringSet("data/trees/7_paracetamol_amidases_controls.txt")

controls_df <- data.frame(
  query_name = names(controls),
  seq = as.character(controls)
) %>% 
  mutate(
    label = word(query_name, sep = "_", 1),
    genus = word(query_name, sep = "_", -2),
    species = word(query_name, sep = "_", -1),
    label = case_when(
      label == "4YJ6" ~ "4YJ6_1_Chain",
      label == "WP091572988.1" ~ "WP_091572988.1",
      TRUE ~ label
    ),
    type = "paracetamol amidases"
  )

# Define active homologs
active_homologs <- c(
  "PKZ01497.1", "PKZ94153.1", "PKZ20744.1", "PLB82905.1", 
  "PLB04707.1", "PMC29638.1", "PKY89575.1", "PKY92403.1",
  "PKY89520.1", "PKY70105.1", "PKY79758.1", "PKZ37694.1",
  "PKY80781.1"
)

# Combine metadata
meta_combined <- controls_df %>%
  select(query_name, seq, label, genus, species, type) %>%
  bind_rows(meta_all %>% select(query_name, seq, label, genus, species, type)) %>%
  mutate(hits = ifelse(label %in% active_homologs, "yes", "no")) %>%
  distinct(seq, .keep_all = TRUE) %>%
  mutate(label = paste0(label, "_", genus, "_", species)) %>%
  remove_rownames()

# Read JGI library
jgi_library <- read.csv("data/trees/JGI_TM1_38_urinary_amidases_order.csv", sep = ";")

# Read and process CLEAN predictions for homologs
clean_homologs <- read.csv("data/CLEAN/20230530_unique_amidases_hits_maxsep_edited.csv", sep = ";", header = TRUE) %>%
  mutate(
    EC1 = sub("EC:", "", EC1) %>% sub("/.*", "", .) %>% na_if(""),
    EC2 = sub("EC:", "", EC2) %>% sub("/.*", "", .) %>% na_if(""),
    EC3 = sub("EC:", "", EC3) %>% sub("/.*", "", .) %>% na_if(""),
    label = Identifier
  )

# Read and process CLEAN predictions for controls
clean_controls <- read.csv("data/CLEAN/7_paracetamol_amidases_controls_maxsep.csv", sep = ";", header = TRUE) %>%
  mutate(
    EC1 = sub("EC:", "", EC1) %>% sub("/.*", "", .) %>% na_if(""),
    EC2 = sub("EC:", "", EC2) %>% sub("/.*", "", .) %>% na_if(""),
    label = Identifier
  )

# Combine CLEAN predictions
clean_combined <- bind_rows(
  clean_homologs %>% mutate(EC3 = ifelse(is.na(EC3), NA, EC3)),
  clean_controls
) %>%
  select(label, EC1, EC2, EC3)

# Merge combined metadata with CLEAN predictions
combined_df <- inner_join(meta_combined, clean_combined, by = "label") %>%
  mutate(
    species = case_when(
      label == "ANB41810.1_Ochrobactrum_sp." ~ "sp. TCC-2",
      label == "ANS81375.1_Ochrobactrum_sp." ~ "sp. PP-2",
      TRUE ~ species
    ),
    EC1 = substr(as.character(EC1), 1, 3),
    EC2 = substr(as.character(EC2), 1, 3),
    selection = if_else(seq %in% jgi_library$coding_seq, "yes", "no")
  )

# Read mapping file and merge with metadata
mapping <- read_xlsx("data/Table_SI_p_notation.xlsx")

met <- data.frame(label = ggtreem$data$label[ggtreem$data$isTip]) %>%
  left_join(combined_df, by = "label") %>%
  mutate(accession_number = sub("^(.+?)_.*", "\\1", label)) %>%
  left_join(mapping %>% select(accession_number, p_notation), by = "accession_number") %>%
  mutate(
    p_notation = case_when(
      accession_number == "ANS81375.1" ~ "Mah",
      accession_number == "ANB41810.1" ~ "TccA",
      accession_number == "4YJ6" ~ "4YJ6",
      accession_number == "AFC37599.1" ~ "AmpA",
      TRUE ~ p_notation
    )
  ) %>%
  select(-selection, -hits)

# Add metadata to the tree
ggtreemet <- ggtreem %<+% met

# Define color palette for EC classes
color_palette <- c(
  "1.1" = "deepskyblue", 
  "1.2" = "blue",
  "1.5" = "black", 
  "3.1" = "darkolivegreen1", 
  "3.4" = "chartreuse",
  "3.5" = "chartreuse3", 
  "3.6" = "darkolivegreen", 
  "5.1" = "violet", 
  "6.3" = "red"
)

# Create the final plot
p <- ggtreemet +
  geom_tippoint(aes(fill = factor(EC1)), shape = 21, size = 2) +
  scale_fill_manual(values = color_palette) +
  geom_tiplab(
    aes(label = paste0("  ", p_notation, "  "), 
        subset = type != "paracetamol amidases" & !is.na(p_notation)),
    size = 2, 
    color = "black"
  ) +
  geom_tiplab(
    aes(label = paste0("  ", p_notation, "  "), 
        subset = type == "paracetamol amidases" & !is.na(p_notation)),
    size = 2, 
    color = "purple"
  ) +
  labs(fill = "Predicted EC") +
  theme(
    legend.position = "bottom",
    legend.margin = margin(t = 0, r = 0, b = 0, l = 10, unit = "pt")
  ) +
  guides(fill = guide_legend(nrow = 1))
p

# Save the plot
ggsave("output/Figure_2.png", plot = p, width = 16, height = 9, dpi = 900)
