library(ape)
library(ggtree)
library(treeio)
library(dplyr)
library(readr)
library(readxl)
library(tidyr)
library(ggplot2)
library(patchwork)
library(phytools)

# File paths
tree_file <- "data/trees/16_hits_tree/16_enzyme_substrate_combinations_v20240704.fasta.contree"
data_file <- "data/processed/hits_matrix_binary_df.csv"

# Customizable parameters
label_size <- 3  # Set consistent label size for both trees

# Read the first tree file
tree <- treeio::read.iqtree(tree_file)
phylo_tree <- as.phylo(tree)
midtr <- midpoint.root(phylo_tree)

# Update the tip labels to only show the p_numbers
midtr$tip.label <- gsub(":.*", "", midtr$tip.label)

# Read the second tree data and perform hierarchical clustering
binary_df <- read_csv(data_file)
ordered_samples <- c("p109", "p151", "p168", "p182", "p167", "p117", "p118", "p197", "p198", "p148", "p128", "p131", "p140", "p162", "p156", "p161")

heatmap_data <- binary_df %>%
  pivot_longer(-sample_name, names_to = "substrate", values_to = "hit") %>%
  mutate(hit = ifelse(hit == TRUE, 1, 0)) %>%
  pivot_wider(names_from = substrate, values_from = hit, values_fill = list(hit = 0)) %>%
  mutate(sample_name = factor(sample_name, levels = ordered_samples)) %>%
  arrange(sample_name) %>%
  filter(rowSums(select(., -sample_name)) > 0)

transposed_data <- t(heatmap_data %>% select(-sample_name))
colnames(transposed_data) <- heatmap_data$sample_name

# Calculate Jaccard similarity index for enzymes
enzymes <- colnames(transposed_data)
jaccard_matrix <- matrix(0, nrow = length(enzymes), ncol = length(enzymes), dimnames = list(enzymes, enzymes))

for (i in 1:length(enzymes)) {
  for (j in 1:length(enzymes)) {
    a <- transposed_data[, i]
    b <- transposed_data[, j]
    jaccard_index <- sum(a & b) / sum(a | b)
    jaccard_matrix[i, j] <- jaccard_index
    jaccard_matrix[j, i] <- jaccard_index
  }
}

# Perform hierarchical clustering
dist_matrix <- as.dist(1 - jaccard_matrix)  # Convert Jaccard similarity to distance
hc <- hclust(dist_matrix)
phylo_tree2 <- as.phylo(hc)

# Plot the first tree
p1 <- ggtree(midtr) +
  geom_tiplab(size = label_size) +
  theme_tree2() +
  theme(plot.margin = unit(c(0, 0, 0, 0), "cm"))  # Adjust left margin

# Plot the second tree
p2 <- ggtree(phylo_tree2, layout = "rectangular", branch.length = "none") + 
  geom_tiplab(size = label_size, offset = -1) +  # Set consistent label size
  theme_tree2() +
  scale_x_reverse() +  # Reverse the x-axis to flip the tree tips to the left
  theme(plot.margin = unit(c(0, 0, 0, 8), "cm"))  # Adjust right margin

# Combine the two plots side by side
combined_plot <- p1 | p2 + plot_layout(widths = c(1, 1))

# Display the combined plot
print(combined_plot)

# Save the combined plot to a file
ggsave("output/Figure_S10.png", plot = combined_plot, width = 16, height = 8, device = "png", dpi=300)
