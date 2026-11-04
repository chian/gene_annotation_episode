library(ggplot2)
library(cowplot)
library(dplyr)
library(tidyr)
library(readr)
library(stringr)

# Function to plot heatmap and bar plots with customizable image and label sizes
plot_heatmap_with_bars <- function(data_file, width, height, label_size, output_file) {
  # Load your data
  binary_df <- read_csv(data_file)
  
  # Reverse the order of the samples to match the tree (reversed order)
  ordered_samples <- c("P109", "P151", "P168", "P182", "P167", "P117", "P118", "P197", "P198", "P148", "P128", "P131", "P140", "P162", "P156", "P161")
  
  # Prepare the data for the heatmap
  heatmap_data <- binary_df %>%
    pivot_longer(-sample_name, names_to = "substrate", values_to = "hit") %>%
    mutate(hit = ifelse(hit == TRUE, 1, 0)) %>%
    pivot_wider(names_from = substrate, values_from = hit, values_fill = list(hit = 0)) %>%
    mutate(sample_name = factor(sample_name, levels = ordered_samples)) %>%
    arrange(sample_name)
  
  # Melt the data for ggplot
  heatmap_data_melt <- heatmap_data %>%
    pivot_longer(-sample_name, names_to = "substrate", values_to = "hit") %>%
    mutate(substrate = case_when(
      substrate == "cap" ~ "capecitabine",
      substrate == "butyrate" ~ "4-NP-butyrate",
      substrate == "trimethyl" ~ "4-NP-trimethylacetate",
      TRUE ~ substrate
    ))
  
  # Calculate the number of hits per sample
  hits_per_sample <- heatmap_data %>%
    rowwise() %>%
    mutate(hits_count = sum(c_across(where(is.numeric)))) %>%
    ungroup()
  
  # Sort the final table according to the specified order
  hits_per_sample <- hits_per_sample %>%
    mutate(sample_name = factor(sample_name, levels = ordered_samples)) %>%
    arrange(sample_name)
  
  # Calculate the number of hits per substrate
  hits_per_substrate <- heatmap_data %>%
    summarise(across(where(is.numeric), sum, .names = "hits_{.col}"))
  
  # Reshape the data to a long format for easier viewing
  hits_per_substrate_long <- hits_per_substrate %>%
    pivot_longer(cols = everything(), names_to = "substrate", values_to = "hits_count") %>%
    mutate(substrate = case_when(
      substrate == "hits_cap" ~ "capecitabine",
      substrate == "hits_butyrate" ~ "4-nitrophenyl-butyrate",
      substrate == "hits_trimethyl" ~ "4-nitrophenyl-trimethylacetate",
      TRUE ~ str_remove(substrate, "^hits_")
    ))
  
  # Plot the heatmap
  heatmap_plot <- ggplot(heatmap_data_melt, aes(x = substrate, y = sample_name, fill = factor(hit))) +
    geom_tile(color = "grey") +
    scale_fill_manual(values = c("transparent", "darkgreen")) +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = 0.5, color = "black", size = label_size), # Adjust vertical justification
          axis.text.y = element_text(color = "black", size = label_size),
          axis.title.x = element_blank(),
          axis.title.y = element_blank(),
          legend.position = "none",
          panel.grid = element_blank(), 
          plot.margin = margin(1,1,1,1))  # Increase margins to ensure everything fits
  
  # Plot the number of hits per sample on the right side
  hits_per_sample_plot <- ggplot(hits_per_sample, aes(y = sample_name, x = hits_count, fill = hits_count)) +
    geom_bar(stat = "identity", color = "grey") +
    geom_text(aes(label = hits_count), hjust = -0.3, size = label_size * 0.5) +
    scale_fill_gradient(low = "lightgreen", high = "darkgreen") +
    scale_x_continuous(limits = c(0, 11), breaks = seq(0, max(hits_per_sample$hits_count), by = 2)) +
    theme_minimal() +
    theme(axis.title.y = element_blank(),
          axis.text.y = element_blank(),
          axis.ticks.y = element_blank(),
          axis.text.x = element_blank(),  # Remove x-axis text numbering
          legend.position = "none",
          panel.grid = element_blank(), 
          plot.margin = margin(1,1,1,1))   # Increase margins to ensure everything fits
  
  
  # Plot the number of hits per substrate on the top
  hits_per_substrate_plot <- ggplot(hits_per_substrate_long, aes(x = substrate, y = hits_count, fill = hits_count)) +
    geom_bar(stat = "identity", color = "grey") +
    geom_text(aes(label = hits_count), vjust = -0.3, size = label_size * 0.5) +
    scale_fill_gradient(low = "lightgreen", high = "darkgreen") +
    scale_y_continuous(limits = c(0, 14), breaks = seq(0, 14, by = 2)) +
    theme_minimal() +
    theme(axis.title.x = element_blank(),
          axis.title.y = element_text(margin = margin(r = 18), size = label_size),
          axis.text.x = element_blank(),
          axis.ticks.x = element_blank(),
          axis.text.y = element_blank(),
          legend.position = "none",
          panel.grid = element_blank(), 
          plot.margin = margin(1, 1, 1, 1)) +  # Increase margins to ensure everything fits
    labs(y = "Number of enzymes")
  
  # Create an empty filler plot for the top right corner
  empty_plot <- ggplot() +
    theme_void()
  
  # Combine the plots using cowplot's plot_grid
  combined_plot <- plot_grid(
    plot_grid(hits_per_substrate_plot, empty_plot, ncol = 2, rel_widths = c(4, 1)),
    plot_grid(heatmap_plot, hits_per_sample_plot, ncol = 2, rel_widths = c(4, 1), align = "h"),
    nrow = 2,
    rel_heights = c(1, 4)
  )
  
  # Save the combined plot as a PNG file with the specified dimensions
  ggsave(output_file, plot = combined_plot, width = width, height = height, dpi = 300)
  
  # Print the combined plot
  print(combined_plot)
}

# Example usage of the function
data_file <- "data/processed/hits_matrix_binary_df.csv"
output_file <- "output/Figure_3B.png"

plot_heatmap_with_bars(data_file, width = 7, height = 9, label_size = 12, output_file = output_file)
