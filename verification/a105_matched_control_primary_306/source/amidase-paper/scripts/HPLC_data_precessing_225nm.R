# Load necessary libraries
library(readxl)
library(dplyr)
library(tidyr)
library(ggplot2)
library(car)
library(tidytext)
library(forcats)  # For fct_reorder()
library(writexl)

# Define the data directory path
data_dir <- "data/HPLC/225/amidase_substrate_screening"

# List all Excel files (.xls) in the directory
file_list <- list.files(
  path = data_dir,
  pattern = "\\.xls$",
  full.names = TRUE
)

# Read the specified range from the 'Integration' sheet of each file into a named list of data frames
# Use basename(file_list) to set the names to base file names
data_list <- setNames(lapply(file_list, function(x) {
  # Extra columns (up to row 60) are imported to ensure all compound integrations are present
  read_excel(
    x,
    sheet = "Integration",
    range = "A40:D60",
    skip = 1  # Skipping the first row within the range as headers
  )
}), basename(file_list))

# CLEANING UP THE TIBBLES
data_list <- lapply(data_list, function(df) {
  # Remove the first two rows and the first column
  df[-c(1, 2), -1]
})

# MERGE INTO A SINGLE DATAFRAME
combined_df <- bind_rows(data_list, .id = "Sample") 

# Names for cleanup below
specific_names <- c(
  "ACE", "diuron", "Desatinib", "CAP", "atenolol",
  "Acetylsulfamethoxazole", "Propanil", "Atovarstatine",
  "chlorpropham", "Metoclopramid", "Rufinamide", "vorinostat"
)

# CLEANING UP THE DATA
cleaned_df <- combined_df %>% 
  filter(!is.na(`Peak Name`)) %>%  # Remove all empty imported rows
  mutate(
    RT = round(as.numeric(`Retention Time`), 1),
    Area = round(as.numeric(Area), 1)  # Make Retention Time and Area numeric and round them to first decimal point
  ) %>%
  separate(
    Sample,
    into = c("name", "replicate", "pool", "timepoint", "batch"),
    sep = "_",
    remove = TRUE,
    extra = "merge",
    fill = "right"
  ) %>%  # Split label into multiple columns
  mutate(
    batch = ifelse(grepl("\\.xls$", batch), batch, NA),  # If batch column ends with .xls, assume it's actually a batch value
    batch = gsub("\\.xls$", "", batch),  # Remove .xls from batch
    name = gsub("\\.xls$", "", name),    # Remove .xls from name
    timepoint = gsub("\\.xls$", "", timepoint)  # Remove .xls from timepoint
  ) %>%
  filter(!is.na(Area)) %>%  # Remove entries with no peak area (different from peak area = 0)
  mutate(name = gsub("100uM", "", name)) %>%  # Remove '100uM' from name
  rename(sample_name = name) %>%  # Rename 'name' column to 'sample_name'
  select(-`Retention Time`) %>%  # Remove 'Retention Time' column
  rename(peak = `Peak Name`) %>% 
  mutate(sample_name = gsub("^AB\\s+", "AB", sample_name)) %>% 
  filter(!(sample_name %in% specific_names & sample_name != peak)) %>%  # Remove erroneous peaks
  group_by(sample_name, replicate, pool, timepoint, batch, peak) %>%  # Remove erroneously integrated peaks
  filter(Area == max(Area)) %>% 
  ungroup() %>% 
  mutate(
    replicate = case_when(
      replicate == "A" ~ 1,
      replicate == "B" ~ 2,
      replicate == "C" ~ 3,
      TRUE ~ as.numeric(replicate)
    ),
    peak = ifelse(peak == "Desatinib", "dasatinib", peak)  # Correct misspelling
  )

## ASSIGNING BATCH NUMBERS
cleaned_df <- cleaned_df %>% 
  mutate(
    sample_name = toupper(sample_name),  # Ensure sample names are uppercase for consistency
    batch = case_when(
      grepl("P(109|110|111|112|113|114|115|116|117|118|119|120|121|122)", sample_name) ~ "b1",
      grepl("P(124|125|126|127|128|129|130|131|132|133|134|135|136|137|138|139|140|141|142|143|144|145|146|147|148|149|150|151)", sample_name) ~ "b2",
      grepl("P(152|153|154|155|156|157|158|159|160|161|162|163|164|165|166|167|168)", sample_name) ~ "b3",
      grepl("P(180|181|182|183|184|185|186|187|188|189|190|191|192|193|194|195|196|197|198|199|200)", sample_name) ~ "b4",
      sample_name %in% c("GORDONIA", "CORYNEBACTERIUM", "LACTOBACILLUS") ~ "b4",
      TRUE ~ batch
    )
  ) %>%
  filter(!is.na(batch))

#### FINDING DUPLICATED ROWS #####

# Check for duplicates based on specific columns
duplicates <- duplicated(cleaned_df[c("sample_name", "pool", "replicate", "timepoint", "batch", "peak")]) | 
  duplicated(cleaned_df[c("sample_name", "pool", "replicate", "timepoint", "batch", "peak")], fromLast = TRUE)

# View duplicate rows
df_duplicated <- cleaned_df[duplicates, ]
print(df_duplicated)

################ FINDING MISSING PEAKS #################

# Define pools and their respective peaks
pool_p1 <- c("diuron", "chlorpropham", "ACE", "vorinostat", "atenolol", "CAP")
pool_p2 <- c("Acetylsulfamethoxazole", "Rufinamide", "Metoclopramid", "Propanil", "Dasatinib", "Atorvastatin")

# Function to fill missing peaks correctly based on the pool
fill_missing_peaks <- function(df, pool_name, pool_peaks) {
  df %>%
    filter(pool == pool_name) %>%
    complete(
      peak = pool_peaks,
      nesting(sample_name, replicate, timepoint, pool, batch),
      fill = list(RT = NA, Area = 0)
    )
}

# Fill for pool p1
p1_filled_df <- fill_missing_peaks(cleaned_df, "p1", pool_p1)

# Fill for pool p2
p2_filled_df <- fill_missing_peaks(cleaned_df, "p2", pool_p2)

# Combine the results
final_cleaned_df <- bind_rows(p1_filled_df, p2_filled_df) %>%
  distinct() %>%
  arrange(sample_name, replicate, timepoint, pool, batch, peak) %>%
  select(sample_name, replicate, timepoint, pool, batch, peak, RT, Area)

# Identify which missing peaks were added
extra_rows <- anti_join(final_cleaned_df, cleaned_df)
print(extra_rows)

###### RENAME Corynebacterium -> P203, Gordonia -> P204, Lactobacillus -> P205

final_cleaned_df <- final_cleaned_df %>% 
  mutate(
    peak = tolower(peak),
    sample_name = toupper(sample_name),
    peak = case_when(
      peak == "ace" ~ "acesulfame",
      peak == "cap" ~ "capecitabine",
      peak == "metoclopramid" ~ "metoclopramide",
      TRUE ~ peak
    ),
    sample_name = case_when(
      sample_name == "CORYNEBACTERIUM" ~ "P203",
      sample_name == "GORDONIA" ~ "P204",
      sample_name == "LACTOBACILLUS" ~ "P205",
      TRUE ~ sample_name
    )
  )

############ PLOTTING S146A ##################

# Filter data for sample_name 'S146A'
cleaned_df_filter <- final_cleaned_df %>%
  filter(!is.na(timepoint), sample_name == "S146A")

# Create the boxplot
plot <- ggplot(cleaned_df_filter, aes(x = sample_name, y = Area, fill = timepoint, color = batch)) +
  geom_boxplot(outlier.shape = NA) +  # Create boxplots; hide outliers for cleaner design
  geom_jitter(width = 0.2, alpha = 0.5, size = 2.5) +  # Add jittered points to show individual data points
  facet_wrap(~peak, scales = "free_y", ncol = 4) +  # Facets split by peak, each with independent y-axis
  labs(
    title = "Distribution of Area by Peak and Timepoint of inactivated enzyme (S146A) 225nm",
    x = "Sample Name",
    y = "Area"
  ) +
  theme_minimal() +
  theme(
    axis.text.x = element_text(angle = 90, vjust = 0.5),  # Set x-axis labels to be vertical
    strip.background = element_blank(),  # Clean up facet labels background
    strip.text.x = element_text(face = "bold"),  # Bold the facet labels
    strip.text.y = element_text(angle = 0)  # Ensure peak labels are readable
  )

# Print the plot
print(plot)

######################################################
### IQR METHOD TO DETECT OUTLIERS (REMOVES ZEROS) ####
######################################################

identify_outliers_iqr <- function(df, column) {
  Q1 <- quantile(df[[column]], 0.25)
  Q3 <- quantile(df[[column]], 0.75)
  IQR_value <- Q3 - Q1
  lower_bound <- Q1 - 1.5 * IQR_value
  upper_bound <- Q3 + 1.5 * IQR_value
  df <- df %>%
    mutate(outlier = ifelse(df[[column]] < lower_bound | df[[column]] > upper_bound, TRUE, FALSE))
  return(df)
}

# Identify outliers in the Area column for 'S146A'
s146a_df <- cleaned_df_filter %>%
  select(-batch, -replicate, -pool, -RT)

s146a_df_with_outliers <- s146a_df %>%
  group_by(peak) %>%
  do(identify_outliers_iqr(., "Area")) %>%
  ungroup()

# Ensure unique rows before merging
s146a_df_with_outliers_unique <- s146a_df_with_outliers %>%
  distinct(sample_name, timepoint, peak, Area, .keep_all = TRUE)

# Merge outlier information back to the final data frame
final_cleaned_df_with_outliers <- final_cleaned_df %>%
  left_join(
    s146a_df_with_outliers_unique %>% select(sample_name, timepoint, peak, Area, outlier),
    by = c("sample_name", "timepoint", "peak", "Area")
  )

# Replace NA in the outlier column with FALSE
final_cleaned_df_with_outliers <- final_cleaned_df_with_outliers %>%
  mutate(outlier = ifelse(is.na(outlier), FALSE, outlier))

# Remove identified outliers
final_cleaned_df_no_outliers <- final_cleaned_df_with_outliers %>%
  filter(!outlier) %>%
  select(-outlier)

# Create a dataframe of the removed outliers (optional)
removed_outliers_df <- final_cleaned_df_with_outliers %>%
  filter(outlier) %>%
  select(-outlier)

# Determine the number of unique peaks for plotting
unique_peaks <- length(unique(final_cleaned_df_no_outliers$peak))
ncol <- ceiling(sqrt(unique_peaks))
nrow <- ceiling(unique_peaks / ncol)

# Plot the result for 'S146A' after removing outliers
plot <- ggplot(
  final_cleaned_df_no_outliers %>%
    filter(sample_name == "S146A") %>%
    filter(peak %in% c("acesulfame", "atenolol", "chlorpropham", "rufinamide")),
  aes(x = sample_name, y = Area, fill = timepoint, color = peak)
) +
  geom_boxplot(outlier.shape = NA) +
  geom_jitter(width = 0.2, alpha = 0.5, size = 2.5) +
  stat_summary(
    fun.data = mean_sdl, fun.args = list(mult = 1),
    geom = "errorbar", width = 0.2, color = "black", position = position_dodge(0.75)
  ) +
  stat_summary(
    fun = mean, geom = "point", shape = 20, size = 3, color = "black", position = position_dodge(0.75)
  ) +
  facet_wrap(~peak, scales = "free_y", nrow = nrow, ncol = ncol) +
  labs(
    title = "Distribution of Area by Peak and Timepoint of inactivated enzyme (S146A) 225nm",
    x = "Sample Name",
    y = "Area"
  ) +
  theme_minimal() +
  theme(
    axis.text.x = element_text(angle = 90, vjust = 0.5),
    strip.background = element_blank(),
    strip.text.x = element_text(face = "bold"),
    strip.text.y = element_text(angle = 0)
  )

# Print the plot
print(plot)

################################################################################################################
############## CALCULATE INDIVIDUAL AREA REMOVAL ###############################################################
################################################################################################################

# Calculate removal and relative removal
df_removal <- final_cleaned_df_no_outliers %>%
  pivot_wider(
    names_from = timepoint,
    values_from = c(RT, Area),
    names_sep = "_",
    values_fn = mean
  ) %>%
  mutate(
    relative_removal = ifelse(
      is.na(Area_t0) | is.na(Area_t24),
      NA,
      ((Area_t0 - Area_t24) / Area_t0) * 100
    )
  )

df_long <- df_removal %>%
  filter(peak %in% c("acesulfame", "atenolol", "chlorpropham", "rufinamide")) %>%
  pivot_longer(
    cols = c(relative_removal), 
    names_to = "metric", 
    values_to = "value"
  ) %>%
  filter(is.finite(value))

#############################
### MEDIAN AND IQR OF EACH ENZYME ###
df_summary_median <- df_long %>%
  filter(metric == "relative_removal") %>%
  group_by(sample_name, peak, metric) %>%
  summarize(
    median_value = median(value, na.rm = TRUE),
    iqr_value = IQR(value, na.rm = TRUE)
  )

df_stats_median <- df_long %>%
  left_join(df_summary_median, by = c("peak", "metric", "sample_name")) %>%
  filter(metric == "relative_removal") 

# Plot the data with median and IQR (interquartile range)
average_iqr_plot <- df_stats_median %>%
  ggplot(aes(x = sample_name, y = median_value, color = as.factor(peak))) + 
  geom_point() +
  geom_errorbar(
    aes(ymin = median_value - 1.5 * iqr_value, ymax = median_value + 1.5 * iqr_value),
    width = 0.2
  ) +
  geom_hline(
    data = . %>% filter(sample_name == "S146A"),
    aes(yintercept = median_value), linetype = "dotted", color = "red"
  ) +
  geom_hline(
    data = . %>% filter(sample_name == "S146A"),
    aes(yintercept = median_value + 1.5 * iqr_value), linetype = "dotted", color = "blue"
  ) +
  geom_hline(
    data = . %>% filter(sample_name == "S146A"),
    aes(yintercept = median_value - 1.5 * iqr_value), linetype = "dotted", color = "blue"
  ) +
  ylim(-120, 120) +
  geom_hline(yintercept = 50, color = "darkgreen") +
  facet_grid(peak ~ metric) +  
  theme_minimal() +
  theme(
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)
  ) +
  labs(
    title = "Relative removal median and IQR with blue IQR lines of S146A control (225nm)",
    x = "Enzyme",
    y = "Relative removal (%)",
    color = "Peak"
  )

# Print and save the plot
print(average_iqr_plot)
write.csv(df_stats_median, "data/processed/data_225nm.csv", row.names = FALSE)

##############
### EXCEL EXPORT ###

s146a_stats_median <- df_stats_median %>%
  filter(sample_name == "S146A") %>%
  group_by(sample_name, metric, peak) %>%
  mutate(
    median_S146A = median_value,
    iqr_S146A = iqr_value,
    threshold_value_median = median_value + 1.5 * iqr_value
  ) %>%
  select(sample_name, metric, peak, median_S146A, iqr_S146A, threshold_value_median)

df_stats_combined <- df_stats_median %>%
  left_join(
    s146a_stats_median,
    by = c("metric", "peak", "sample_name"),
    relationship = "many-to-many"
  ) %>%
  select(-Area_t0, -Area_t24, -RT_t0, -RT_t24, -value) 

fill_with_s146a <- function(df) {
  if ("S146A" %in% df$sample_name) {
    s146a_values <- df %>% filter(sample_name == "S146A")
    df <- df %>%
      mutate(across(everything(), ~ ifelse(is.na(.), s146a_values[[cur_column()]], .)))
  }
  return(df)
}

df_stats_combined_filled <- df_stats_combined %>%
  group_by(metric, peak) %>%
  group_modify(~ fill_with_s146a(.x)) %>%
  ungroup()

# Filter based on the threshold value
hits <- df_stats_combined_filled %>%
  group_by(metric, peak) %>%
  filter(
    (median_value > threshold_value_median) &
      median_value > 50 &
      metric == "relative_removal"
  ) %>%
  select(sample_name, median_value, threshold_value_median, metric, peak) %>%
  distinct() %>%
  mutate(wavelength = 225)

hits
