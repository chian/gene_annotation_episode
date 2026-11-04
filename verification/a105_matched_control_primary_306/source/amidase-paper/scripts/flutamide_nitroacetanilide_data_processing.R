# Processing the plate reader data of the amidase substrate screening with colorimetric substrates

# Load necessary packages
library("readxl")
library("janitor")
library("reshape2")
library("ggplot2")
library("viridis")
library("dplyr")
library("scales")
library("openxlsx")
library("stringr")

# Read templates
folder_layout <- "plate_reader_substrate_screening/layout"
folder_path <- file.path("data", folder_layout)

file_path_templates <- list.files(folder_path, pattern = "TM", full.names = TRUE)
file_path_templates <- file_path_templates[!grepl("~", file_path_templates)]

# Initialize list to store templates
templates <- list()

for (file_path in file_path_templates) {
  temp <- read_excel(file_path, range = "B1:M9") %>%
    janitor::clean_names() %>%
    as.matrix() %>%
    t() %>%
    as.vector()
  
  templates[[basename(file_path)]] <- temp
}

# Import the flutamide and nitroacetanilide plate reader data
# Define the ranges for the plate reader data in the export files
ranges_flut_nitro <- list(
  p109_to_p122 = "B40:CU761",
  p124_to_p151 = "B40:CU762",
  p152_to_p168 = "B40:CU686",
  p180_to_p200 = "B40:CU735"
)

all_data_410 <- list()

folder_data <- "plate_reader_substrate_screening"
folder_path <- file.path("data", folder_data)

# Template assignment
for (rep in names(ranges_flut_nitro)) {
  tmafils <- list.files(folder_path, full.names = TRUE)
  tmafils <- tmafils[!grepl("~|layout|4NP", tmafils)]
  templates <- templates[!grepl("~|4NP", names(templates))]
  tmarep <- tmafils[str_detect(tmafils, rep)]
  
  if (length(tmarep) > 0) {
    tma <- read_excel(tmarep, range = ranges_flut_nitro[[rep]], col_types = c("date", rep("numeric", 97)))
    
    # Select the appropriate template based on the filename
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
    mutate(variable = gsub("\\.[[:digit:]]+", "", variable)) %>%
    mutate(
      substrate = str_extract(variable, "(?<=_).*$"),  # Extract everything after '_'
      variable = gsub("_.*", "", variable)  # Remove everything after and including '_'
    ) %>%
    mutate(substrate = if_else(is.na(substrate), as.character(variable), substrate)) %>%
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
mean_S146A_data <- dat %>%
  filter(variable == "S146A") %>%
  group_by(time, set, substrate) %>%
  summarise(mean_S146A = mean(mean, na.rm = TRUE), .groups = 'drop')

# Join the S146A means back to the original dataset
dat_adjusted_S146A <- dat %>%
  left_join(mean_S146A_data, by = c("time", "set", "substrate")) %>%
  mutate(mean_normalized = mean - mean_S146A)

# Prepare the full dataset for plotting and rename variables
full_data <- dat_adjusted_S146A %>%
  filter(time == 1250) %>%
  mutate(variable = recode(variable,
                           "lactob" = "P205",
                           "Cory" = "P203",
                           "Gord" = "P204"),
         variable = toupper(variable)) %>%
  filter(!variable %in% c("FLUTAMIDE", "FLUTAMIDE TP", "NITROACETANILIDE", "NITROANILINE"))

# Separate data for flutamide and nitroacetanilide
data_flutamide <- full_data %>%
  filter(substrate == "flutamide")

data_nitroacetanilide <- full_data %>%
  filter(substrate == "nitroacetanilide")

# Ensure dat_time also has the renaming and capitalization applied
dat_time_flutamide <- dat_adjusted_S146A %>%
  filter(time == 1250) %>%
  mutate(variable = recode(variable,
                           "lactob" = "P205",
                           "Cory" = "P203",
                           "Gord" = "P204"),
         variable = toupper(variable)) %>%
  filter(variable == "S146A" & substrate == "flutamide")

dat_time_nitroacetanilide <- dat_adjusted_S146A %>%
  filter(time == 1250) %>%
  mutate(variable = recode(variable,
                           "lactob" = "P205",
                           "Cory" = "P203",
                           "Gord" = "P204"),
         variable = toupper(variable)) %>%
  filter(variable == "S146A" & substrate == "nitroacetanilide")

# Create the plot for flutamide
gg_flutamide <- ggplot(data_flutamide, aes(x = variable, y = mean_normalized, fill = variable)) +
  geom_point(size = 3, color = "black") +
  geom_errorbar(aes(ymin = mean_normalized - (2 * sd), ymax = mean_normalized + (2 * sd)),
                width = 0.2, color = "black") +
  labs(x = "Enzyme", y = "Normalized OD410", size = 16) +
  scale_fill_viridis(discrete = TRUE) +
  facet_wrap(~ set, scales = "free_x", nrow = 1) +
  geom_hline(data = dat_time_flutamide,
             aes(yintercept = mean_normalized + (2 * sd), group = set),
             linetype = "dotted", color = "red", size = 1) +
  geom_hline(data = dat_time_flutamide,
             aes(yintercept = mean_normalized - (2 * sd), group = set),
             linetype = "dotted", color = "red", size = 1) +
  scale_y_continuous(
    limits = c(-0.4, 0.8),                            # Set y-axis limits
    breaks = seq(-0.4, 0.8, by = 0.2)   
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

gg_flutamide

# Save the plot
ggsave("output/Figure_S5_flutamide.png", plot = gg_flutamide, width = 14, height = 5, dpi = 300)

# Create the plot for nitroacetanilide
gg_nitroacetanilide <- ggplot(data_nitroacetanilide, aes(x = variable, y = mean_normalized, fill = variable)) +
  geom_point(size = 3, color = "black") +
  geom_errorbar(aes(ymin = mean_normalized - (2 * sd), ymax = mean_normalized + (2 * sd)),
                width = 0.2, color = "black") +
  labs(x = "Enzyme", y = "Normalized OD410", size = 16) +
  scale_fill_viridis(discrete = TRUE) +
  facet_wrap(~ set, scales = "free_x", nrow = 1) +
  geom_hline(data = dat_time_nitroacetanilide,
             aes(yintercept = mean_normalized + (2 * sd), group = set),
             linetype = "dotted", color = "red", size = 1) +
  geom_hline(data = dat_time_nitroacetanilide,
             aes(yintercept = mean_normalized - (2 * sd), group = set),
             linetype = "dotted", color = "red", size = 1) +
  scale_y_continuous(
    limits = c(-0.4, 1),                            # Set y-axis limits
    breaks = seq(-0.4, 1, by = 0.2)                 # Set y-axis ticks every 0.2
  ) +
  theme_minimal() +
  theme(
    legend.position = "none",
    strip.text = element_blank(),
    axis.text.x = element_text(angle = 90, hjust = 1, size = 14),  # Match x-axis text size
    axis.text.y = element_text(size = 16),                          # Match y-axis text size
    axis.title.x = element_text(size = 16),                         # Increase x-axis title size
    axis.title.y = element_text(size = 16),                         # Increase y-axis title size
    panel.spacing = unit(1, "lines")
  )

gg_nitroacetanilide

# Save the plot with updated dimensions
ggsave("output/Figure_S5_nitroacetanilide.png", plot = gg_nitroacetanilide, width = 14, height = 5, dpi = 300)
# Filter the hits
# Combine dat_time for both substrates
dat_time_combined <- bind_rows(dat_time_flutamide, dat_time_nitroacetanilide)

# Merge full_data with dat_time_combined to get mean_S146A and sd_S146A values
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
  mutate(wavelength = 400)

# Save the hits dataset as an Excel file
write.xlsx(hits, file = "data/processed/screening_hits/flutamide_nitroacetanilide_hits.xlsx")
