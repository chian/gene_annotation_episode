library(ggmsa)
library(ggplot2)
library(gridExtra)
library(Biostrings)

# Function to plot MSA
plot_msa <- function(alignment_file, ordered_samples, start_pos, end_pos, positions_per_row, label_positions, width, height, label_size, output_file) {
  # Read the alignment file
  alignment <- readAAStringSet(alignment_file)
  
  # Reorder the alignment based on the desired order
  ordered_alignment <- alignment[ordered_samples]
  
  # Calculate the number of rows needed
  num_rows <- ceiling((end_pos - start_pos + 1) / positions_per_row)
  
  # Create a plot for each row
  plots <- list()
  for (i in 1:num_rows) {
    row_start <- start_pos + (i - 1) * positions_per_row
    row_end <- min(start_pos + i * positions_per_row - 1, end_pos)
    p <- ggmsa(ordered_alignment, start = row_start, end = row_end, color = "Clustal", font = "DroidSansMono", seq_name = TRUE) +
      theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = 0.5, size = label_size, color = "black", margin = margin(t = 5)),  # Adjust x-axis label size
            axis.text.y = element_text(size = label_size, color = "black")) +  # Adjust y-axis label size
      scale_x_continuous(breaks = intersect(label_positions, seq(row_start, row_end)))
    plots[[i]] <- p
  }
  
  
  # Arrange the plots into a single plot without pagination
  alignment_plot <- arrangeGrob(grobs = plots, ncol = 1)
  
  # Save the alignment plot to a file
  ggsave(output_file, plot = alignment_plot, width = width, height = height, units = "cm")  # Adjust width and height
  
  # Print the alignment plot
  print(alignment_plot)
}

# Example usage
alignment_file <- "data/alignment/16_enzyme_substrate_combinations.fasta"
ordered_samples <- c("P161", "P156", "P162", "P140", "P131", "P128", "P148", "P198", "P197", "P118", "P117", "P167", "P182", "P168", "P151", "P109")
start_pos <- 226
end_pos <- 387
positions_per_row <- 81
label_positions <- c(226,256,266,269,300,329,366,368)
width <- 20
height <- 10
label_size <- 7
output_file <- "output/Figure_5A.png"

plot_msa(alignment_file, ordered_samples, start_pos, end_pos, positions_per_row, label_positions, width, height, label_size, output_file)