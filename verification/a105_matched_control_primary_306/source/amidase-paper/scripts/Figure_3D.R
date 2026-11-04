# Load necessary libraries
library(ggplot2)
library(ggrepel)
library(dplyr)

# Import the substrate matrix CSV file
substrate_matrix <- read.csv("data/processed/hits_matrix_binary_df.csv")

# Rename columns to have consistent substrate names
colnames(substrate_matrix) <- sub("cap", "capecitabine", colnames(substrate_matrix))
colnames(substrate_matrix) <- sub("trimethyl", "4NP-trimethylacetate", colnames(substrate_matrix))
colnames(substrate_matrix) <- sub("butyrate", "4NP-butyrate", colnames(substrate_matrix))
substrate_matrix$sample_name <- toupper(substrate_matrix$sample_name)

# Convert boolean values to numeric (0/1) for all columns except 'sample_name'
substrate_matrix <- substrate_matrix %>%
  mutate(across(-sample_name, ~ ifelse(. == TRUE, 1, 0)))

# Perform PCA on the binary data (excluding 'sample_name')
# Select variables with non-zero variance
pca_binary_data <- substrate_matrix %>%
  select(-sample_name) %>%
  select_if(~ var(.) > 0)

# Perform PCA with scaling
pca_binary_result <- prcomp(pca_binary_data, scale. = TRUE)

# Extract PCA scores and add sample names
pca_scores <- as.data.frame(pca_binary_result$x)
pca_scores$sample_name <- substrate_matrix$sample_name

# Extract PCA loadings and add variable names
pca_loadings <- as.data.frame(pca_binary_result$rotation)
pca_loadings$variable <- rownames(pca_loadings)

# Extract percentage of variance explained for PC1 and PC2
var_explained <- summary(pca_binary_result)$importance[2, ]
pc1_var <- round(var_explained[1] * 100, 1)
pc2_var <- round(var_explained[2] * 100, 1)

# Create the biplot with sample names as labels and PCA loadings
biplot_gg <- ggplot() +
  # Plot the PCA loadings as arrows
  geom_segment(
    data = pca_loadings,
    aes(x = 0, y = 0, xend = PC1 * 7, yend = PC2 * 7),
    arrow = arrow(length = unit(0.2, "cm")),
    color = "violet",
    size = 1
  ) +
  # Add labels for the PCA loadings (variables)
  geom_text_repel(
    data = pca_loadings,
    aes(x = PC1 * 7, y = PC2 * 7, label = variable),
    color = "darkviolet",
    size = 6,
    nudge_x = 0.15,
    nudge_y = 0.2
  ) +
  # Add labels for the samples (PCA scores)
  geom_text_repel(
    data = pca_scores,
    aes(x = PC1, y = PC2, label = sample_name),
    size = 6
  ) +
  # Customize axis labels with variance explained
  xlab(paste0("PC1 (", pc1_var, "% variance explained)")) +
  ylab(paste0("PC2 (", pc2_var, "% variance explained)")) +
  # Apply minimal theme and customize appearance
  theme_minimal() +
  theme(
    panel.grid.major = element_blank(), 
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 1.2),
    axis.ticks = element_line(color = "black", size = 1),
    axis.title = element_text(size = 16),
    axis.text = element_text(size = 14, color = "black")
  )

# Print the biplot
print(biplot_gg)

# Save the plot to a file
ggsave("output/Figure_4D.png", plot = biplot_gg, width = 9, height = 6, dpi = 600)
