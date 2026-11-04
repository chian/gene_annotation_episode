# Processing the plate reader data of the amidase substrate screening with colorimetric substrates

# Load necessary packages
library("tidyverse")
library("readxl")
library("janitor")
library("reshape2")
library("viridis")
library("openxlsx")
library("scales")

# Read templates
folder_layout <- "plate_reader_substrate_screening/layout"
folder_path <- file.path("data", folder_layout)

file_path_templates <- list.files(folder_path, pattern = "TM", full.names = TRUE)
file_path_templates <- file_path_templates[!grepl("~", file_path_templates)]

# Initialize lists to store templates
templates <- list()

for (file_path in file_path_templates) {
  temp <- read_excel(file_path, range = "B1:M9") %>%
    janitor::clean_names() %>%
    as.matrix(bycol = TRUE) %>%
    t() %>%
    as.vector()
  
  templates[[basename(file_path)]] <- temp
}

# Import the 4NP substrate plate reader data
# Define the ranges for the plate reader data in the export files
ranges_4NP <- list(
  p109_to_p122 = "B41:CU762",
  p124_to_p151 = "B41:CU762",
  p152_to_p168 = "B41:CU762",
  p180_to_p200 = "B29:CU750"
)

all_data_410 <- list()

folder_data <- "plate_reader_substrate_screening"
folder_path <- file.path("data", folder_data)

# Template assignment
for (rep in names(ranges_4NP)) {
  tmafils <- list.files(folder_path, full.names = TRUE)
  tmafils <- tmafils[!grepl("~|layout|flutamide", tmafils)]
  templates <- templates[!grepl("~|flutamide", names(templates))]
  tmarep <- tmafils[str_detect(tmafils, rep)]
  
  if (length(tmarep) > 0) {
    tma <- read_excel(tmarep, range = ranges_4NP[[rep]], col_types = c("date", rep("numeric", 97)))
    
    # Select the appropriate template based on the filename or other logic
    template <- templates[grepl(rep, names(templates))]
    
    newnam <- c("time", "temperature_c", paste0(unlist(template)))
    colnames(tma) <- make.unique(newnam)
    
    tma$replicate <- rep
    all_data_410[[rep]] <- tma
  }
}

# Combine all data into a single dataframe
combined_data_410 <- bind_rows(all_data_410)

# Function to clean and adjust data
clean_and_adjust_data <- function(combined_data) {
  combined_cleaned <- combined_data %>%
    select(-temperature_c) %>%   # Remove the column for temperature (constant at 37°C)
    filter(!grepl("Time", time)) %>%  # Remove duplicate time rows
    mutate(time = round(as.numeric(difftime(time, as.POSIXct("1899-12-30", tz = "UTC"), units = "mins")), 0)) %>%
    select(-contains("NA"))
  
  # Convert from wide to long format while preserving replicate information
  combined_long <- melt(combined_cleaned, id.vars = c('time', 'replicate')) %>%
    mutate(value = as.numeric(value)) %>%
    mutate(variable = gsub("\\.[[:digit:]]", "", variable)) %>%
    mutate(
      substrate = str_extract(variable, "(?<=_).*$"),  # Extract everything after '_'
      variable = gsub("_.*", "", variable)  # Remove everything after and including '_'
    ) %>%
    mutate(substrate = if_else(is.na(substrate), "4-NP", substrate)) %>%
    filter(!is.na(value))
  
  # Adjust time so that all start from 0 and proceed in multiples of 1 minute
  adjusted_combined_long <- combined_long %>%
    group_by(replicate) %>%
    mutate(time = time - min(time)) %>%
    ungroup()
  
  return(adjusted_combined_long)
}

# Apply the function
adjusted_combined_long_410 <- clean_and_adjust_data(combined_data_410) %>%
  rename(set = replicate)

# Average biological triplicates
dat <- adjusted_combined_long_410 %>%
  group_by(time, variable, set, substrate) %>%
  summarise(
    mean = mean(value, na.rm = TRUE),
    sd = sd(value, na.rm = TRUE)
  ) %>%
  ungroup()

# Normalize means
# Extract means for 'S146A' with 'butyrate' and 'trimethyl'
mean_S146A_data <- dat %>%
  filter(variable == "S146A") %>%
  group_by(time, set, substrate) %>%
  summarise(mean_S146A = mean(mean, na.rm = TRUE), .groups = 'drop')

# Join the S146A means back to the original dataset
dat_adjusted_S146A <- dat %>%
  left_join(mean_S146A_data, by = c("time", "set", "substrate")) %>%
  mutate(mean_normalized = mean - mean_S146A) %>%
  filter(substrate %in% c("butyrate", "trimethyl"))

# Prepare the full dataset for plotting and rename variables
full_data_butyrate <- dat_adjusted_S146A %>%
  filter(time == 100) %>%
  mutate(variable = recode(variable,
                           "lactob" = "P205",
                           "Cory" = "P203",
                           "Gord" = "P204"),
         variable = toupper(variable)) %>%
  filter(!variable %in% c("BUTYRATE", "TRIMETHYL", "4-NP") & substrate == "butyrate")

full_data_trimethyl <- dat_adjusted_S146A %>%
  filter(time == 600) %>%
  mutate(variable = recode(variable,
                           "lactob" = "P205",
                           "Cory" = "P203",
                           "Gord" = "P204"),
         variable = toupper(variable)) %>%
  filter(!variable %in% c("BUTYRATE", "TRIMETHYL", "4-NP") & substrate == "trimethyl")

# Ensure dat_time also has the renaming and capitalization applied
dat_time_butyrate <- dat_adjusted_S146A %>%
  filter(time == 100) %>%
  mutate(variable = recode(variable,
                           "lactob" = "P205",
                           "Cory" = "P203",
                           "Gord" = "P204"),
         variable = toupper(variable)) %>%
  filter(variable == "S146A" & substrate == "butyrate")

dat_time_trimethyl <- dat_adjusted_S146A %>%
  filter(time == 600) %>%
  mutate(variable = recode(variable,
                           "lactob" = "P205",
                           "Cory" = "P203",
                           "Gord" = "P204"),
         variable = toupper(variable)) %>%
  filter(variable == "S146A" & substrate == "trimethyl")

# Create the plot for 4NP-butyrate
gg_butyrate <- ggplot(full_data_butyrate, aes(x = variable, y = mean_normalized, fill = variable)) +
  geom_point(size = 3, color = "black") +
  geom_errorbar(aes(ymin = mean_normalized - (2 * sd), ymax = mean_normalized + (2 * sd)),
                width = 0.2, color = "black") +
  labs(x = "Enzyme", y = "Normalized OD410", size = 16) +
  scale_fill_viridis(discrete = TRUE) +
  facet_wrap(~ set, scales = "free_x", nrow = 1) +
  geom_hline(data = dat_time_butyrate,
             aes(yintercept = mean_normalized + (2 * sd), group = set),
             linetype = "dotted", color = "red", size = 1) +
  geom_hline(data = dat_time_butyrate,
             aes(yintercept = mean_normalized - (2 * sd), group = set),
             linetype = "dotted", color = "red", size = 1) +
  scale_y_continuous(
    limits = c(-1, 2),                            # Set y-axis limits
    breaks = seq(-1, 2, by = 0.2)                 # Set y-axis ticks every 0.2
  ) +
  theme_minimal() +
  theme(
    legend.position = "none",
    strip.text = element_blank(),
    axis.text.x = element_text(angle = 90, hjust = 1, size = 14),
    axis.text.y = element_text(size = 16),
    axis.title.x = element_text(size = 16),
    axis.title.y = element_text(size = 16),
    panel.spacing = unit(1, "lines")
  )

gg_butyrate

# Save the plot with updated dimensions
ggsave("output/Figure_S5_4NP-butyrate.png", plot = gg_butyrate, width = 14, height = 5, dpi = 300)

# Create the plot for 4NP-trimethylacetate
gg_trimethyl <- ggplot(full_data_trimethyl, aes(x = variable, y = mean_normalized, fill = variable)) +
  geom_point(size = 3, color = "black") +
  geom_errorbar(
    aes(ymin = mean_normalized - (2 * sd), ymax = mean_normalized + (2 * sd)),
    width = 0.2, color = "black"
  ) +
  labs(x = "Enzyme", y = "Normalized OD410", size = 16) +
  scale_fill_viridis(discrete = TRUE) +
  facet_wrap(~ set, scales = "free_x", nrow = 1) +
  geom_hline(
    data = dat_time_trimethyl,
    aes(yintercept = mean_normalized + (2 * sd), group = set),
    linetype = "dotted", color = "red", size = 1
  ) +
  geom_hline(
    data = dat_time_trimethyl,
    aes(yintercept = mean_normalized - (2 * sd), group = set),
    linetype = "dotted", color = "red", size = 1
  ) +
  scale_y_continuous(
    limits = c(-1, 2),                            # Set y-axis limits
    breaks = seq(-1, 2, by = 0.4)                 # Set y-axis ticks every 0.4
  ) +
  theme_minimal() +
  theme(
    legend.position = "none",
    strip.text = element_blank(),
    axis.text.x = element_text(angle = 90, hjust = 1, size = 14),
    axis.text.y = element_text(size = 16),
    axis.title.x = element_text(size = 16),  # Increase x-axis title size
    axis.title.y = element_text(size = 16),  # Increase y-axis title size
    panel.spacing = unit(1, "lines")
  )

gg_trimethyl

# Save the plot with updated dimensions
ggsave("output/Figure_S5_4NP-trimethylacetate.png", plot = gg_trimethyl, width = 14, height = 5, dpi = 300)

# Export hits
# Combine dat_time for both substrates
dat_time_combined <- bind_rows(dat_time_butyrate, dat_time_trimethyl)

# Merge full_data with dat_time_combined to get mean_S146A and sd_S146A values
full_data <- bind_rows(full_data_butyrate, full_data_trimethyl)
joined_data <- full_data %>%
  inner_join(dat_time_combined, by = c("set", "substrate"), suffix = c("", "_dat_time"))

# Filter rows where mean_normalized is higher than 2 times the sd of dat_time
hits <- joined_data %>%
  mutate(threshold = 2 * sd_dat_time) %>%
  filter(mean_normalized > threshold)

# Select relevant columns
hits <- hits %>%
  select(variable, substrate, mean_normalized, threshold) %>%
  rename(
    sample_name = variable,
    peak = substrate,
    Yield = mean_normalized
  ) %>%
  mutate(wavelength = 410)

# Save the hits dataset as a CSV file
write.xlsx(hits, "data/processed/screening_hits/hits_4NP_substrates.xlsx")
