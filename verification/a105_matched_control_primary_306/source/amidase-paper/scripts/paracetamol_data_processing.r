# Processing the plate reader data of the amidase substrate screening with colorimetric substrates

# Load necessary packages
library("readxl")
library("janitor")
library("reshape2")
library("ggplot2")
library("viridis")
library("dplyr")
library("zoo")
library("openxlsx")

# Set the enzyme and file paths
enzym <- "paracetamol_library_screen"
folder_path <- file.path("data/plate_reader_substrate_screening", enzym)
file_path_template <- list.files(folder_path, pattern = "template", full.names = TRUE)
file_path_template <- file_path_template[!grepl("~", file_path_template)]

# Read in the plate template
temp <- read_excel(file_path_template, skip = 2, range = "B3:M11") %>%
  janitor::clean_names() %>%
  as.matrix() %>%
  t() %>%
  as.vector()

temp <- ifelse(temp == "t7 S146A", "S146A", temp)
temp <- ifelse(temp == "T 7 PLA", "lactob", temp)

# Existing OD400 ranges for each replicate
replicates_ranges_od400 <- list(
  repA = "B995:CU1919",
  repB = "B29:CU944",
  repC = "B28:CU928"
)

all_data_400 <- list()

# Loop through each replicate and its range
for (rep in names(replicates_ranges_od400)) {
  # Construct file paths
  tmafils <- list.files(folder_path, pattern = enzym, full.names = TRUE)
  tmafils <- tmafils[!grepl("~|setup|Bradford|screenshot|split|Template|Tris|endpoint", tmafils)]
  tmarep <- tmafils[grep(rep, tmafils)]
  
  # Read in the data for the current replicate
  tma <- read_excel(tmarep, range = replicates_ranges_od400[[rep]], col_types = c("date", rep("numeric", 97)))
  tma[grepl("OVRFLW", tma)] <- 4.0  # Replace "OVRFLW" with max plate reader value
  
  # Prepare column names
  newnam <- c("time", "temperature_c", paste0(temp))
  colnames(tma) <- make.unique(newnam)
  
  # Add a column to identify the replicate
  tma$replicate <- rep
  
  # Store the processed data
  all_data_400[[rep]] <- tma
}

# Combine all data into a single dataframe
combined_data_400 <- bind_rows(all_data_400)

# Function to clean and adjust data
clean_and_adjust_data <- function(combined_data) {
  combined_cleaned <- combined_data %>%
    select(-temperature_c) %>%   # Remove temperature column
    filter(!grepl("Time", time)) %>%  # Remove duplicate time rows
    mutate(time = round(as.numeric(difftime(time, as.POSIXct("1899-12-30", tz = "UTC"), units = "mins")), 0)) %>%
    select(-contains("NA.")) %>%  # Remove columns generated for NAs during import
    select(time, matches("p|lactob|S146A"), replicate)  # Keep relevant columns
  
  # Convert from wide to long format while preserving replicate information
  combined_long <- melt(combined_cleaned, id.vars = c('time', 'replicate')) %>%
    mutate(value = as.numeric(value)) %>%
    mutate(variable = gsub("\\.[[:digit:]]", "", variable))
  
  # Adjust time so that all start from 0 and proceed in multiples of 3 minutes
  adjusted_combined_long <- combined_long %>%
    group_by(replicate) %>%
    mutate(
      time = time - min(time),
      time = round(time / 3) * 3
    ) %>%
    ungroup()
  
  return(adjusted_combined_long)
}

# Apply the function to the data
adjusted_combined_long <- clean_and_adjust_data(combined_data_400)

# Average duplicate measurements within each replicate
averaged_within_replicate <- adjusted_combined_long %>%
  group_by(replicate, time, variable) %>%
  summarise(average_value = mean(value, na.rm = TRUE)) %>%
  ungroup()

# Calculate the average and standard deviation across replicates
dat <- averaged_within_replicate %>%
  group_by(time, variable) %>%
  summarise(
    mean = mean(average_value, na.rm = TRUE),
    sd = sd(average_value, na.rm = TRUE)
  ) %>%
  ungroup()

# Calculate mean of inactive S146A control to normalize the data
mean_S146A_data <- dat %>%
  filter(variable == "S146A") %>%
  group_by(time) %>%
  summarise(mean_S146A = mean(mean, na.rm = TRUE), .groups = 'drop')

# Calculate rolling mean over 30 minutes to smooth out the noise
dat_adjusted_S146A <- dat %>%
  left_join(mean_S146A_data, by = "time") %>%
  mutate(
    mean_normalized = mean - mean_S146A
  ) %>%
  arrange(time) %>%
  group_by(variable) %>%
  mutate(
    rolling_mean = rollapply(mean_normalized, width = 10, FUN = mean, fill = NA, align = "center"),
    rolling_sd = rollapply(sd, width = 10, FUN = mean, fill = NA, align = "center")
  ) %>%
  ungroup()

# Ensure that rolling_mean and rolling_sd for S146A are zero
dat_adjusted_S146A <- dat_adjusted_S146A %>%
  mutate(
    rolling_mean = if_else(variable == "S146A", 0, rolling_mean),
    rolling_sd = if_else(variable == "S146A", 0, rolling_sd)
  )

# Plot the data
gg <- ggplot(dat_adjusted_S146A, aes(x = time, y = rolling_mean, group = variable)) +
  geom_line(aes(color = variable)) +
  geom_line(data = dat_adjusted_S146A %>% filter(variable == "S146A"), aes(x = time, y = rolling_mean), color = "red", size = 1.5) +
  scale_color_viridis(discrete = TRUE, option = "D") +
  labs(x = "Time (minutes)", y = "Mean ± SD", title = "Substrate screening with paracetamol normalized by S146A hydrolysis (red line)") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "right") +
  xlim(0, 2600)

print(gg)

# Evaluate the normalized OD at time 2600
full_data <- dat_adjusted_S146A %>%
  filter(time == 2601) %>%
  mutate(variable = recode(variable, "lactob" = "P205"),
         variable = toupper(variable))

# Filter data for S146A
dat_S146A <- full_data %>%
  filter(variable == "S146A")

# Calculate the mean and 2 * sd for S146A
mean_S146A <- dat_S146A$rolling_mean
sd_S146A <- dat_S146A$sd
upper_bound_S146A <- mean_S146A + (2 * sd_S146A)
lower_bound_S146A <- mean_S146A - (2 * sd_S146A)

# Create the plot
gg <- ggplot(full_data, aes(x = variable, y = rolling_mean)) +
  geom_point(size = 3, color = "black") +
  geom_errorbar(aes(ymin = rolling_mean - (2 * rolling_sd), ymax = rolling_mean + (2 * rolling_sd)),
                width = 0.2, color = "black") +
  geom_errorbar(data = dat_S146A,
                aes(ymin = rolling_mean - (2 * sd_S146A), ymax = rolling_mean + (2 * sd_S146A)),
                width = 0.2, color = "black") +
  geom_hline(yintercept = upper_bound_S146A, linetype = "dashed", color = "red", size = 1) +
  geom_hline(yintercept = lower_bound_S146A, linetype = "dashed", color = "red", size = 1) +
  labs(x = "Enzyme", y = "Normalized OD400", size = 16) +
  scale_y_continuous(
    limits = c(-0.4, 1.1),                            # Set y-axis limits
    breaks = seq(-0.4, 1.2, by = 0.2)                 # Set y-axis ticks every 0.2
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

gg

# Save the plot with updated dimensions
ggsave("output/Figure_S5_paracetamol.png", plot = gg, width = 14, height = 5, dpi = 300)

# Identify the hits
threshold_S146A <- 2 * sd_S146A

hits <- full_data %>%
  filter(rolling_mean > threshold_S146A) %>%
  select(variable, rolling_mean) %>%
  rename(sample_name = variable, Yield = rolling_mean) %>%
  mutate(peak = "paracetamol", wavelength = 400)

# Save the hits to an Excel file
write.xlsx(hits, file = "data/processed/screening_hits/paracetamol_hits.xlsx")
