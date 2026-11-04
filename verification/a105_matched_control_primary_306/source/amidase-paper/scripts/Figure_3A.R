library(ggtree)
library(treeio)
library(ggplot2)
library(dplyr)
library(readr)
library(readxl)


# Function to plot the tree with customizable image size and ratio
plot_tree_with_custom_size <- function(tree_file, metadata_file, pnot_file, width, height, output_file, 
                                       dot_size = 2, label_size = 3, branch_size = 0.5) {
  # Read the tree file
  tree <- treeio::read.iqtree(tree_file)
  phylo_tree <- as.phylo(tree)
  midtr <- midpoint.root(phylo_tree)
  
  # Update the tip labels to only show the p_numbers
  midtr$tip.label <- gsub(":.*", "", midtr$tip.label)
  
  # Read metadata for bootstrap values
  meta_all <- read_csv(metadata_file) %>% 
    dplyr::mutate(label = word(query_name, sep = "_", 3)) %>% 
    dplyr::mutate(type = "homolog")
  
  pnot <- read_excel(pnot_file) %>%
    select(label = p_notation, seq = seq)
  
  merg2 <- pnot %>%
    left_join(., meta_all, by = "seq") %>%
    dplyr::group_by(seq) %>%
    dplyr::slice(1)
  
  # Visualize the tree using ggtree and add bootstrap values
  p <- ggtree(midtr, layout = "rectangular", size = branch_size) %<+% merg2 + 
    geom_tiplab(size = label_size) +
    theme_tree2() +
    theme(axis.text.x = element_blank(), axis.ticks.x = element_blank(), axis.title.x = element_blank(),
          legend.text = element_text(size = 12),
          legend.position = c(0.1, 0.9),  # Position legend at the top left
          legend.justification = c(0, 1), 
          plot.margin = margin(10, 10, 10, 10))  # Add margin to ensure no elements are cut off
  
  # Initialize the color and size vectors
  node_colors <- rep("gray80", length(p$data$label))
  node_sizes <- rep(0.1, length(p$data$label))
  
  # Update color and size based on bootstrap values
  node_colors[!p$data$isTip & as.numeric(p$data$label) > 50] <- "gray90"
  node_colors[!p$data$isTip & as.numeric(p$data$label) > 75] <- "gray30"
  node_colors[!p$data$isTip & as.numeric(p$data$label) > 90] <- "black"
  
  node_sizes[!p$data$isTip & as.numeric(p$data$label) > 50] <- dot_size
  
  # Add the points with the correct colors and sizes
  p <- p +
    geom_nodepoint(aes(subset = !isTip, color = node_colors, size = node_sizes, shape = I(19))) +
    scale_color_manual(name = "Bootstrap Value", values = c("gray90" = "gray90", "gray30" = "gray30", "black" = "black"),
                       labels = c("90-100", "75-89", "50-74")) +
    guides(color = guide_legend(override.aes = list(size = dot_size)), size = "none") +
    coord_cartesian(clip = 'off')  # Ensure that nothing gets cut off
  
  # Save the tree plot as a PNG file with the specified dimensions
  ggsave(output_file, plot = p, width = width, height = height, dpi = 300)
  
  # Print the tree plot
  print(p)
}

# File paths
tree_file <- "data/trees/16_hits_tree/16_enzyme_substrate_combinations_v20240704.fasta.contree"
metadata_file <- "data/trees/20230515_metadata_376_amidases_hit.csv"
pnot_file <- "data/AS_library.xlsx"
output_file <- "output/Figure_3A.png"

# Example usage of the function
plot_tree_with_custom_size(tree_file, metadata_file, pnot_file, width = 10, height = 8, output_file, 
                           dot_size = 4, label_size = 6, branch_size = 1)
