# Load necessary libraries
library(dplyr)
library(readxl)
library(readr)
library(tidyr)

############################
# Read and preprocess data
############################

# Get list of files in the specified directory
file_list <- list.files(path = "data/processed/screening_hits", full.names = TRUE)

# Identify the sample names file by searching for "sample_name" in the filenames
sample_name_file <- grep("sample_name", file_list, value = TRUE, ignore.case = TRUE)

# Read the sample names file
sample_name <- read_excel(sample_name_file, col_names = FALSE)
colnames(sample_name) <- "sample_name"

# Exclude the sample names file from the list of data files
data_files <- setdiff(file_list, sample_name_file)

# Read data from the data files into a list
data_list <- lapply(data_files, read_excel)

# Combine the data frames into one
combined_df <- bind_rows(data_list)


#######################################
# Calculate removal metrics
#######################################

# Process HPLC data
df_HPLC <- combined_df %>%
  filter(!is.na(metric)) %>%
  group_by(peak, metric) %>%
  mutate(removal = median_value) %>%
  ungroup()

# Process colorimetric data
df_colorimetric <- combined_df %>%
  filter(is.na(metric)) %>%
  group_by(peak) %>%
  mutate(removal = 100 * (Yield / max(Yield))) %>%  # Removal calculated with respect to the highest yield
  ungroup()

# Merge data frames and apply removal threshold
merged_df <- bind_rows(df_HPLC, df_colorimetric) %>%
  mutate(peak = tolower(peak)) %>%
  mutate(peak = ifelse(peak == "metoclopramid", "metoclopramide", peak)) %>%
  filter(removal > 50)  # Keep only entries with removal over 50%

#######################################
# Generate enzyme-substrate combinations
#######################################

# List of all substrates
all_peaks <- c("rufinamide", "chlorpropham", "acesulfame", "acetylsulfamethoxazole",
               "atenolol", "atorvastatin", "butyrate", "capecitabine", "dasatinib", "diuron",
               "flutamide", "metoclopramide", "nitroacetanilide", "paracetamol",
               "propanil", "trimethyl", "vorinostat")

binary_matrix <- table(merged_df$sample_name, merged_df$peak)
binary_matrix <- as.data.frame.matrix(binary_matrix)

missing_substrates <- c("acesulfame", "dasatinib", "atorvastatin", "metoclopramide",
                        "rufinamide", "chlorpropham", "atenolol", "diuron")

for (s in missing_substrates) {
  binary_matrix[[s]] <- 0
}

# Ensure all substrates are present in the binary matrix
missing_peaks <- setdiff(all_peaks, names(binary_matrix))
for (s in missing_peaks) {
  binary_matrix[[s]] <- 0
}

# Convert counts to logical values (hit or no hit)
binary_matrix <- binary_matrix > 0

# Convert the logical matrix to a data frame
binary_df <- as.data.frame(binary_matrix)
binary_df$sample_name <- rownames(binary_matrix)

# Reorder columns to have 'sample_name' first
binary_df <- binary_df %>%
  select(sample_name, everything())

#######################################
# Write the binary matrix to CSV
#######################################

write_csv(binary_df, "data/processed/hits_matrix_binary_df.csv")

#######################################
# Create long format data for combinations
#######################################

# Convert binary data to long format for output
long_df <- binary_df %>%
  pivot_longer(cols = -sample_name, names_to = "substrate", values_to = "hit") %>%
  mutate(hit_bool = ifelse(hit, 1, 0)) %>%
  select(sample_name, substrate, hit_bool)

#######################################
# Write the enzyme-substrate combinations to CSV
#######################################

write_csv(long_df, "data/processed/272_enzyme_substrate_combinations.csv")
