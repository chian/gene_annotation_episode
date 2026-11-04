library(dplyr)
library(ggplot2)
library(patchwork)
library(corrplot)
library(ggrepel)

# Import the substrate matrix CSV file and process it
substrate_matrix <- read.csv("data/screening_hits/20240708_hits_matrix_binary_df.csv") # Rename columns correctly once
colnames(substrate_matrix) <- sub("cap", "capecitabine", colnames(substrate_matrix))
colnames(substrate_matrix) <- sub("trimethyl", "4NP-trimethylacetate", colnames(substrate_matrix))
colnames(substrate_matrix) <- sub("butyrate", "4NP-butyrate", colnames(substrate_matrix))
substrate_matrix$sample_name <- toupper(substrate_matrix$sample_name)


# Convert boolean values to numeric (0/1) for all columns except 'sample_name'
substrate_matrix <- substrate_matrix %>%
  mutate(across(-sample_name, ~ ifelse(. == TRUE, 1, 0)))

# Perform PCA on the binary data
pca_binary_data <- substrate_matrix %>% select(-sample_name) %>% select_if(~ var(.) > 0)
pca_binary_result <- prcomp(pca_binary_data, scale. = TRUE)

# Plot PCA results with sample names
pca_binary_df <- as.data.frame(pca_binary_result$x)
pca_binary_df$Dataframe <- substrate_matrix$sample_name

# Add color coding based on sample names
pca_binary_df$Color <- ifelse(pca_binary_df$Dataframe %in% c("p131", "p148", "p162"), "darkgreen",
                              ifelse(pca_binary_df$Dataframe %in% c("p161", "p156", "p128", "p168", "p151"), "orange", "blue"))

# Plot PCA results
plot_pca <- ggplot(pca_binary_df, aes(x = PC1, y = PC2, color = Color, label = Dataframe)) +
  geom_point() +
  geom_text(vjust = 1.5, hjust = 1.5) +
  scale_color_identity() +
  ggtitle("PCA of Binary Data Only")

print(plot_pca)

# Sum of Substrates Analysis
# Calculate the sum of substrates for each sample
substrate_sums <- substrate_matrix %>%
  rowwise() %>%
  mutate(sum_substrates = sum(c_across(-sample_name))) %>%
  select(sample_name, sum_substrates)

# Merge the substrate sums with the PCA scores
combined_data <- left_join(pca_binary_df, substrate_sums, by = c("Dataframe" = "sample_name"))

# Perform multiple regression analysis predicting sum of substrates using PCA components
regression_model <- lm(sum_substrates ~ PC1 , data = combined_data)
summary(regression_model)

# Fit the linear model
regression_model <- lm(sum_substrates ~ PC1, data = combined_data)
r_squared <- summary(regression_model)$r.squared

# Visualize the regression results with R-squared
plot_regression <- ggplot(combined_data, aes(x = PC1, y = sum_substrates)) +
  geom_point(size = 6) +
  geom_smooth(method = "lm", size = 1, formula = y ~ x) +
  geom_text_repel(aes(label = Dataframe), 
                  box.padding = 1, 
                  point.padding = 1, 
                  segment.color = 'grey50', 
                  size = 5,
                  direction = "y",  # Prefer placing labels above or below
                  force = 10) +      # Increase the repulsion force
  labs(x = "PC1", y = "#substrates") +
  theme_minimal() +
  scale_y_continuous(breaks = seq(0, 8, by = 2)) + # Show multiples of 2 on the y-axis
  theme(
    panel.grid.major = element_blank(), 
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 1.2),  # Thicker axis lines
    axis.ticks = element_line(color = "black", size = 1.2),  # Thicker axis ticks
    axis.title.x = element_text(size = 16),  # Increase x-axis title size
    axis.title.y = element_text(size = 16),  # Increase y-axis title size
    axis.text.x = element_text(size = 14),  # Increase x-axis tick label size
    axis.text.y = element_text(size = 14),  # Increase y-axis tick label size
    plot.background = element_rect(fill = "white", color = NA)
  ) +
  annotate("text", x = Inf, y = -Inf, label = paste("R² =", round(r_squared, 2)), 
           hjust = 1.1, vjust = -1.1, size = 5)

# Print the plot
print(plot_regression)

ggsave("regression_plot.png", plot = plot_regression, width = 9, height = 6, dpi =600)


######## PC1 LOADINGS ###############################
loadings_pc1 <- pca_binary_result$rotation[, 1]
print(loadings_pc1)

####### BIPLOT #################################
# Standard biplot
biplot(pca_binary_result, scale = 0)

pca_scores <- as.data.frame(pca_binary_result$x)
pca_scores$sample_name <- substrate_matrix$sample_name
pca_scores$Color <- ifelse(pca_scores$sample_name %in% c("P131", "P148", "P162"), "darkgreen",
                           ifelse(pca_scores$sample_name %in% c("P161", "P156", "P128", "P168", "P151"), "orange", "blue"))

pca_loadings <- as.data.frame(pca_binary_result$rotation)
pca_loadings$variable <- rownames(pca_loadings)

# Extract percentage of variance explained
var_explained <- summary(pca_binary_result)$importance[2, ]
pc1_var <- round(var_explained[1] * 100, 1)
pc2_var <- round(var_explained[2] * 100, 1)

biplot_gg <- ggplot() +
  geom_point(data = pca_scores, aes(x = PC1, y = PC2, color = Color), size = 6) +
  geom_text_repel(data = pca_scores, aes(x = PC1, y = PC2, label = sample_name), size = 5, vjust = 1.7, hjust = 1.7) +
  geom_segment(data = pca_loadings, aes(x = 0, y = 0, xend = PC1 * 4, yend = PC2 * 4), arrow = arrow(length = unit(0.2, "cm")), color = "violet", size = 1) +
  geom_text_repel(data = pca_loadings, aes(x = PC1 * 4, y = PC2 * 4, label = variable), color = "darkviolet", size = 5, nudge_x = 0.15, nudge_y = 0.2) +
  scale_color_identity() +
  xlab(paste0("PC1 (", pc1_var, "% variance explained)")) +
  ylab(paste0("PC2 (", pc2_var, "% variance explained)")) +
  theme_minimal() +
  theme(
    panel.grid.major = element_blank(), 
    panel.grid.minor = element_blank(),
    axis.line = element_line(color = "black", size = 1.2),  # Thicker axis lines
    axis.ticks = element_line(color = "black", size = 1),  # Thicker axis ticks
    axis.title = element_text(size = 16),  # Increase the size of the axis labels
    axis.text = element_text(size = 14, color = "black")  # Increase the size of the axis numbers
  )

print(biplot_gg)
ggsave("PCA_biplot.png", plot = biplot_gg, width = 9, height = 6, dpi =600)


####### PLOT SUBSTRATE CORRELATION PLOT ############

# Correlation Analysis
cor_matrix_binary <- cor(pca_binary_data)
print(cor_matrix_binary)

# Visualize correlation matrix
corrplot(cor_matrix_binary, method = "circle") # default is pearson correlation


# Correct column renaming only once
colnames(substrate_matrix) <- sub("cap", "capecitabine", colnames(substrate_matrix))
colnames(substrate_matrix) <- sub("trimethyl", "4NP-trimethylacetate", colnames(substrate_matrix))
colnames(substrate_matrix) <- sub("butyrate", "4NP-butyrate", colnames(substrate_matrix))

# Remove columns with zero standard deviation
non_constant_columns <- substrate_matrix %>%
  select(-sample_name) %>%
  select_if(~ var(.) != 0)

# Calculate the correlation matrix for the relevant columns
cor_matrix <- cor(non_constant_columns, use = "complete.obs")

# Mask negative correlations by setting them to 0
cor_matrix[cor_matrix < 0] <- 0

#png("correlation_plot.png", width = 1000, height = 800, res = 300)

# Create the corrplot
corrplot(cor_matrix, method = "circle", 
         type = "upper", 
         tl.col = "black",  # Set label color to black
         tl.srt = 90, # Rotate labels for better readability
         tl.cex = 1.5,
         order = "hclust",  # Order by hierarchical clustering
         addrect = 2,  # Add rectangles around the clusters
         col = colorRampPalette(c("white", "blue"))(200),
         addCoef.col = "black",  # Add correlation coefficients in black color
         number.cex = 1.5,
         cl.cex = 1.5,  # Increase the size of the legend text
         cl.length = 5,  # Number of levels in the color legend
         cl.ratio = 0.2, 
         is.corr = FALSE,  # Treat the input as not a correlation matrix
         cl.lim = c(0, 1))# Adjust the size of the numbers

# Close the PNG device
#dev.off()

#######
non_constant_columns <- substrate_matrix %>%
  select(-sample_name) %>%
  select_if(~ var(.) != 0)

# Calculate the correlation matrix for the relevant columns
cor_matrix <- cor(non_constant_columns)


# Create the corrplot
corrplot(cor_matrix, method = "circle", 
         type = "upper", 
         tl.col = "black",  # Set label color to black
         tl.srt = 90,  # Rotate labels for better readability
         order = "hclust",  # Order by hierarchical clustering
         addrect = 2,  # Add rectangles around the clusters
         col = colorRampPalette(c("red", "white", "blue"))(200),
         addCoef.col = "black",  # Add correlation coefficients in black color
         number.cex = 1)# Adjust the size of the numbers


