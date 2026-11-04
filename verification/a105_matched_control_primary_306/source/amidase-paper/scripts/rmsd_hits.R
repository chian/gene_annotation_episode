library(dplyr)
library(readr)
library(readxl)
library(janitor)
library(reshape2)
library(tidyr)

# Function to read and clean individual DALI result files
read_and_clean_dali <- function(file_path, query) {
  df <- read_table(file_path, skip = 2, col_names = TRUE) %>%
    dplyr::slice(1:16) %>%
    dplyr::mutate(query = query)
  return(df)
}

# Read all DALI result files with their respective query values
s001 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s001A.txt", "p109")
s002 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s002A.txt", "P117")
s003 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s003A.txt", "P118")
s004 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s004A.txt", "P128")
s005 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s005A.txt", "P131")
s006 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s006A.txt", "P140")
s007 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s007A.txt", "P148")
s008 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s008A.txt", "P151")
s009 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s009A.txt", "P156")
s010 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s010A.txt", "P161")
s011 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s011A.txt", "P162")
s012 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s012A.txt", "P167")
s013 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s013A.txt", "P168")
s014 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s014A.txt", "P182")
s015 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s015A.txt", "P197")
s016 <- read_and_clean_dali("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/s016A.txt", "P198")

# Key
key2 <- read_excel("modeling/alphafold_models/Alphafold Models Amidases/AF3/DALI/rmsd_key.xlsx", col_names = FALSE) %>%
  janitor::clean_names()

# Merge
leftjoin <- bind_rows(s001, s002, s003, s004, s005, s006, s007, s008, s009, s010, s011, s012, s013, s014, s015, s016) %>%
  janitor::clean_names() %>%
  mutate(comparison = paste0(gsub("-A", "", no), 'A')) %>%
  left_join(., key2, by = c("comparison" = "x1"))

# Make a RMSD matrix
matr <- leftjoin %>%
  select(z, query, x2) %>%
  reshape2::dcast(query ~ x2, value.var = "z")

write_csv(matr, "output/rmsd_matrix.csv")

# Check data types in the matrix
str(matr)

# Convert the dataframe to numeric matrix values
numeric_matrix <- apply(matr[, -1], 2, as.numeric)
rownames(numeric_matrix) <- matr$query

# Create a mask to exclude the diagonal values
mask <- !diag(nrow(numeric_matrix))

# Extract the off-diagonal values
off_diagonal_values <- numeric_matrix[mask]

# Check the values in the off-diagonal
print(off_diagonal_values)

# Calculate the average of the off-diagonal values
average_rmsd <- mean(off_diagonal_values, na.rm = TRUE)

# Calculate the standard deviation of the off-diagonal values
sd_rmsd <- sd(off_diagonal_values, na.rm = TRUE)

# Output the results
print(paste("Average RMSD:", average_rmsd))
print(paste("Standard Deviation:", sd_rmsd))
