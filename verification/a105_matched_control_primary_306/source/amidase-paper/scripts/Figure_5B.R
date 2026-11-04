library(ggseqlogo)
library(cowplot)
library(Biostrings)
library(tidyverse)
library(ggpubr)

# Function to plot sequence logos
plot_sequence_logos <- function(alignment_file, promiscuous_set, not_promiscuous_set, label_positions, width, height, label_size, output_file) {
  # Read the alignment file
  alignment <- readAAStringSet(alignment_file)
  
  # Create dataframes for the sets
  create_dataframes <- function(sample_set, label_positions, alignment) {
    dataframes_list <- list()
    for (pos in label_positions) {
      aa_letters <- sapply(alignment, function(x) substr(as.character(x), pos, pos))
      df <- data.frame(Sample = sample_set, AminoAcid = aa_letters[match(sample_set, names(alignment))])
      dataframes_list[[paste0("Position_", pos)]] <- df
    }
    return(dataframes_list)
  }
  
  # Create dataframes for both sets
  promiscuous_dataframes <- create_dataframes(promiscuous_set, label_positions, alignment)
  not_promiscuous_dataframes <- create_dataframes(not_promiscuous_set, label_positions, alignment)
  
  # Sort label_positions in ascending order
  label_positions <- sort(label_positions)
  
  # Create sequence logo plots
  plot_list <- list()
  for (pos in label_positions) {
    # Promiscuous set
    df_promiscuous <- promiscuous_dataframes[[paste0("Position_", pos)]]
    aa_seq_promiscuous <- as.character(df_promiscuous$AminoAcid)
    p_promiscuous <- ggseqlogo(aa_seq_promiscuous, method = "prob") + 
      ggtitle(paste("≥8 substrates")) +
      theme(axis.text.x = element_blank(), axis.ticks.x = element_blank(), legend.position = "none", 
            plot.margin = margin(2, 2, 2, 2), plot.title = element_text(size = label_size), axis.title.y = element_blank())
    
    # Not promiscuous set
    df_not_promiscuous <- not_promiscuous_dataframes[[paste0("Position_", pos)]]
    aa_seq_not_promiscuous <- as.character(df_not_promiscuous$AminoAcid)
    p_not_promiscuous <- ggseqlogo(aa_seq_not_promiscuous, method = "prob") + 
      ggtitle(paste("≤2 substrates")) +
      theme(axis.text.x = element_blank(), axis.ticks.x = element_blank(), legend.position = "none",
            plot.margin = margin(2, 2, 2, 2), plot.title = element_text(size = label_size), axis.title.y = element_blank())
    
    # Combine the plots side-by-side
    combined_plot <- plot_grid(p_promiscuous, p_not_promiscuous, ncol = 2, align = 'h')
    
    # Add frame around the combined plot
    combined_plot <- ggdraw(combined_plot) + 
      theme(plot.margin = margin(1, 1, 1, 1), panel.border = element_rect(colour = "black", fill=NA, size=1))
    
    # Add position label
    combined_plot <- annotate_figure(combined_plot, top = text_grob(paste("Position", pos), 
                                                                    color = "black", face = "bold", size = label_size))
    
    plot_list[[paste0("Position_", pos)]] <- combined_plot
  }
  
  # Combine all position plots into a single plot with grid lines
  final_combined_plot <- plot_grid(plotlist = plot_list, ncol = 4, nrow = 3, align = 'v')  # Adjust number of columns and rows
  
  # Save the combined plot as an image file
  ggsave(output_file, final_combined_plot, width = width, height = height)  # Adjust width and height
  
  # Print the combined plot
  print(final_combined_plot)
}

# Example usage
alignment_file <- "data/alignment/16_enzyme_substrate_combinations_v20240704.fasta"
promiscuous_set <- c("p131", "p148", "p162", "p161", "p168")
not_promiscuous_set <- c("p109", "p140", "p198", "p197", "p118", "p167", "p182")
label_positions <- c(226,256,266,269,300,329,366,368)
width <- 10
height <- 5
label_size <- 10
output_file <- "20240716_sequence_logos_p161_p168.png"

plot_sequence_logos(alignment_file, promiscuous_set, not_promiscuous_set, label_positions, width, height, label_size, output_file)
