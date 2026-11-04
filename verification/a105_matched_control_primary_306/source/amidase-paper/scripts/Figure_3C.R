# Load necessary libraries
library(dplyr)
library(corrplot)

# Import and process the substrate matrix CSV file
substrate_matrix <- read.csv("data/processed/hits_matrix_binary_df.csv")

# Rename columns for clarity
colnames(substrate_matrix) <- sub("cap", "capecitabine", colnames(substrate_matrix))
colnames(substrate_matrix) <- sub("trimethyl", "4NP-trimethylacetate", colnames(substrate_matrix))
colnames(substrate_matrix) <- sub("butyrate", "4NP-butyrate", colnames(substrate_matrix))

# Convert sample names to uppercase
substrate_matrix$sample_name <- toupper(substrate_matrix$sample_name)

# Remove the 'sample_name' column and any columns with zero variance
non_constant_columns <- substrate_matrix %>%
  select(-sample_name) %>%
  select_if(~ var(.) != 0)

# Calculate the correlation matrix using complete observations
cor_matrix <- cor(non_constant_columns, use = "complete.obs")

# Mask negative correlations by setting them to 0
cor_matrix[cor_matrix < 0] <- 0

# Save the correlation plot as a PNG file with squares
png("Figure_3C.png", width = 2000, height = 1600, res = 300)

corrplot(
  cor_matrix, 
  method = "square",             # Changed from "circle" to "square"
  type = "upper", 
  tl.col = "black",              # Label color
  tl.srt = 45,                   # Rotate labels for better readability
  tl.cex = 1.2,                  # Label size adjusted
  order = "hclust",              # Hierarchical clustering order
  addrect = 2,                   # Add rectangles around clusters
  col = colorRampPalette(c("white", "blue"))(200), # Color palette
  addCoef.col = "black",         # Add correlation coefficients in black
  number.cex = 0.8,              # Coefficient size adjusted
  cl.cex = 1.2,                  # Legend text size adjusted
  cl.length = 5,                 # Number of legend levels
  cl.ratio = 0.2,                # Legend size ratio
  is.corr = TRUE,                # Correctly set to TRUE for correlation matrix
  cl.lim = c(0, 1)               # Legend limits
)

# Close the PNG device to save the file
dev.off()
