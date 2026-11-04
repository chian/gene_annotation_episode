library(tidyverse)
library(openxlsx)
library(dplyr)

# Define the paths to the Excel files
compound_results_file <- "output/leave_one_compound_out_results.xlsx"
enzyme_results_file <- "output/leave_one_enzyme_out_results.xlsx"

# Read the "Feature Importance" sheets from the Excel files
# For the leave-one-compound-out results
feature_importance_compound <- read.xlsx(compound_results_file, sheet = "Feature Importance")

# For the leave-one-enzyme-out results
feature_importance_enzyme <- read.xlsx(enzyme_results_file, sheet = "Feature Importance")

# Calculate average importance, standard deviation, and frequency for each feature
# For Compounds
feature_importance_compound_summary <- feature_importance_compound %>%
  group_by(Feature) %>%
  summarize(
    AverageImportance = mean(Overall),
    StdDevImportance = sd(Overall),
    Frequency = n()
  ) %>%
  arrange(desc(AverageImportance))

# For Enzymes
feature_importance_enzyme_summary <- feature_importance_enzyme %>%
  group_by(Feature) %>%
  summarize(
    AverageImportance = mean(Overall),
    StdDevImportance = sd(Overall),
    Frequency = n()
  ) %>%
  arrange(desc(AverageImportance))

# View the summaries
print("Feature Importance Summary for Compounds:")
print(feature_importance_compound_summary)

print("Feature Importance Summary for Enzymes:")
print(feature_importance_enzyme_summary)

# Select the top 30 features based on AverageImportance
top_n_features <- 30

# For Compounds
top_features_compound <- feature_importance_compound_summary %>%
  arrange(desc(AverageImportance)) %>%
  dplyr::slice(1:top_n_features)

# For Enzymes
top_features_enzyme <- feature_importance_enzyme_summary %>%
  arrange(desc(AverageImportance)) %>%
  dplyr::slice(1:top_n_features)

# Feature renaming
rename_features <- function(df) {
  new_names <- c(
    "ANILIDE" = "aryl amide",
    "MW" = "molecule mass",
    "MW_bond" = "amide tail mass",
    "MW_ring" = "aryl mass",
    "Ncharges" = "# charges",
    "N" = "# nitrogen",
    "C" = "# carbon",
    "O" = "# oxygen",
    "R3N" = "# tertiary amine",
    "Cl" = "# chlorine",
    "S" = "# sulfur",
    "R2NH" = "# secondary amine",
    "RCOOR" = "# esters",
    "RINGS" = "# aromatic rings",
    "ROH" = "# hydroxy"
  )
  df$Feature <- sapply(df$Feature, function(x) ifelse(x %in% names(new_names), new_names[x], x))
  return(df)
}

# Apply renaming to the top features
top_features_compound <- rename_features(top_features_compound)
top_features_enzyme <- rename_features(top_features_enzyme)

# For Compounds
importance_plot_compound <- ggplot(top_features_compound, aes(x = reorder(Feature, AverageImportance), y = AverageImportance)) +
  geom_bar(stat = "identity", fill = "orange", color = "black") +
  geom_errorbar(aes(ymin = pmax(0, AverageImportance - StdDevImportance), ymax = AverageImportance + StdDevImportance),
                width = 0.2, color = "black") +
  coord_flip() +
  labs(title = "Chemical and amino acid feature importance of leave-one-chemical-out models",
       y = "Scaled importance") +
  theme_classic(base_size = 18) + 
  theme(
    axis.text.x = element_text(vjust = 1),
    plot.title = element_text(hjust = 0.5, size = 20, face = "bold"),
    axis.text = element_text(size = 18, color = "black"),
    axis.title = element_text(size = 18),
    axis.title.y = element_blank()
  )

# For Enzymes
importance_plot_enzyme <- ggplot(top_features_enzyme, aes(x = reorder(Feature, AverageImportance), y = AverageImportance)) +
  geom_bar(stat = "identity", fill = "forestgreen", color = "black") +
  geom_errorbar(aes(ymin = pmax(0, AverageImportance - StdDevImportance), ymax = AverageImportance + StdDevImportance),
                width = 0.2, color = "black") +
  coord_flip() +
  labs(title = "Chemical and amino acid feature importance of leave-one-enzyme-out models",
       y = "Scaled importance") +
  theme_classic(base_size = 18) + 
  theme(
    axis.text.x = element_text(vjust = 1),
    plot.title = element_text(hjust = 0.5, size = 20, face = "bold"),
    axis.text = element_text(size = 18, color = "black"),
    axis.title = element_text(size = 18),
    axis.title.y = element_blank()
  )

# Print the plots
print(importance_plot_compound)
print(importance_plot_enzyme)

# Save the plots as high-quality images
ggsave("output/Figure_S12_compounds.png", plot = importance_plot_compound, width = 15, height = 10, dpi = 300)
ggsave("output/Figure_S12_enzymes.png", plot = importance_plot_enzyme, width = 15, height = 10, dpi = 300)
