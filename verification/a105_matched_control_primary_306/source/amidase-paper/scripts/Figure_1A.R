library(dplyr)
library(readxl)
library(ggplot2)

# Define the function to create the curve plot
create_paracetamol_curve <- function(file_path, plot_width_cm, plot_height_cm, label_size, output_path) {
  # Read the Excel file into a dataframe
  df <- read_excel(file_path)
  
  # Filter out the abiotic columns
  df <- df %>% 
    select(Time = `Time [h]`, Average_inact, SD_inact, Average_bio, SD_bio)
  
  # Create the plot
  p <- ggplot(df, aes(x = Time)) +
    geom_line(aes(y = Average_inact, color = "Inactive enzyme"), size = 1.5) +
    geom_errorbar(aes(x = Time, ymin = Average_inact - SD_inact, ymax = Average_inact + SD_inact), color = "black", width = 2) +
    geom_line(aes(y = Average_bio, color = "Enzyme"), size = 1.5) +
    geom_errorbar(aes(x = Time, ymin = Average_bio - SD_bio, ymax = Average_bio + SD_bio), color = "black", width = 2) +
    scale_color_manual(values = c("Inactive enzyme" = "grey", "Enzyme" = "blue")) +
    labs(x = "Time (h)",
         y = "Paracetamol concentration (mg/L)",
         color = NULL) +
    theme_minimal() +
    theme(axis.text.x = element_text(color = "black", size = label_size),
          axis.text.y = element_text(color = "black", size = label_size),
          axis.title.x = element_text(color = "black", size = label_size, margin = margin(t = 10)),
          axis.title.y = element_text(color = "black", size = label_size, margin = margin(r = 10)),
          plot.title = element_text(color = "black", size = label_size, hjust = 0.5),
          legend.position = "none",  # Remove the legend
          panel.grid.major = element_blank(), 
          panel.grid.minor = element_blank(),
          axis.line = element_line(color = "black"))  # Add axis lines in black
  
  # Save the plot as a PNG file
  ggsave(output_path, plot = p, width = plot_width_cm, height = plot_height_cm, units = "cm")
}

# Call the function with updated parameters
create_paracetamol_curve(
  file_path = "data/PLA55254_P205_paracetamol_curve.xlsx",
  plot_width_cm = 12,
  plot_height_cm = 12,
  label_size = 12,
  output_path = "output/paracetamol_curve_plot.png"
)
