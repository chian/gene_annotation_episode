library(ggplot2)
library(caret)

# Load the model from the RDS file
xgb_model_filtered <- readRDS("output/machine_learning/xgboost_final_model.rds")

# Generate variable importance plot
xgb_imp_filtered <- varImp(xgb_model_filtered, scale = TRUE)
xgb_imp_filtered <- as.data.frame(xgb_imp_filtered$importance)

# Rename the features
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
    "Cl" = "# shlorine",
    "S" = "# sulfur",
    "R2NH" = "# secondary amine",
    "RCOOR" = "# esters",
    "RINGS" = "# aromatic rings",
    "aa300_size" = "amino acid 300 size",
    "aa226_size" = "amino acid 226 size",
    "aa366_size" = "amino acid 366 size",
    "aa300_secondarystruct" = "amino acid 300 secondary structure",
    "aa266_size" = "amino acid 266 size",
    "aa226_polarity" = "amino acid 266 polarity",
    "aa269_size" = "amino acid 269 size",
    "aa368_polarity" = "amino acid 368 polarity",
    "aa329_polarity" = "amino acid 329 polarity",
    "aa256_polarity" = "amino acid 256 polarity"
    )
  rownames(df) <- sapply(rownames(df), function(x) ifelse(x %in% names(new_names), new_names[x], x))
  return(df)
}

# Apply renaming
xgb_imp_filtered <- rename_features(xgb_imp_filtered)

# Create the ggplot object
importance_plot <- ggplot(xgb_imp_filtered, aes(x = reorder(rownames(xgb_imp_filtered), Overall), y = Overall)) +
  geom_bar(stat = "identity", fill = "steelblue", color="black") +
  coord_flip() +
  labs(title = "Chemical and amino acid feature importance",
       y = "Scaled importance") +
  theme_classic(base_size = 18) + 
  theme(axis.text.x = element_text(vjust = 1),
        plot.title = element_text(hjust = 0.5, size = 20, face = "bold"),
        axis.text = element_text(size = 18, color = "black"),
        axis.title = element_text(size = 18),
        axis.title.y = element_blank())

# Print the plot
print(importance_plot)


# Save the plot as a high-quality, square image
ggsave("output/Figure_4.png", plot = importance_plot, width = 15, height = 10, dpi = 300)

