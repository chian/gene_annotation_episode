# Load necessary libraries
library(dplyr)
library(ggplot2)

df_225nm <- read.csv("data/processed/data_225nm.csv")
df_252nm <- read.csv("data/processed/data_252nm.csv")
df_305nm <- read.csv("data/processed/data_305nm.csv")

# Add a column to distinguish the datasets
df_225nm <- df_225nm %>% mutate(wavelength = 225)
df_252nm <- df_252nm %>% mutate(wavelength = 252)
df_305nm <- df_305nm %>% mutate(wavelength = 305)

# Combine all datasets
df_combined <- bind_rows(df_225nm, df_252nm, df_305nm)

df_filtered <- df_combined %>%
  filter(!is.na(median_value))

average_iqr_plot_filtered <- df_filtered %>%
  ggplot(aes(x = sample_name, y = median_value, color = as.factor(peak))) + 
  geom_point(size = 3) +
  geom_errorbar(aes(ymin = median_value - 1.5 * iqr_value, ymax = median_value + 1.5 * iqr_value), width = 0.2) +
  geom_hline(data = . %>% filter(sample_name == "S146A"), 
             aes(yintercept = median_value), linetype = "dotted", color = "red", linewidth = 1.5) +
  geom_hline(data = . %>% filter(sample_name == "S146A"), 
             aes(yintercept = median_value + 1.5 * iqr_value), linetype = "dotted", color = "blue", linewidth = 1.5) +
  geom_hline(data = . %>% filter(sample_name == "S146A"), 
             aes(yintercept = median_value - 1.5 * iqr_value), linetype = "dotted", color = "blue", linewidth = 1.5) +
  ylim(-120, 120) +
  geom_hline(yintercept = 50, color = "darkgreen", linewidth = 1.5) +
  facet_wrap(~ peak, ncol = 2, scales = "free_x") +  
  theme_minimal() +
  theme(
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1, size = 14),
    axis.text.y = element_text(size = 16),
    strip.text.y = element_blank(),  # Remove facet labels
    strip.text = element_text(size = 16, face = "bold"),
    axis.title.x = element_blank(),  # Remove individual x-axis labels
    axis.title.y = element_text(size = 18),  # Adjust y-axis label size
    legend.position = "none",
    plot.margin = margin(t = 1, r = 1, b = 1, l = 1, unit = "cm")
  ) +
  labs(y = "Relative removal (%)",
       color = "Peak"
  )

# Print the plot
print(average_iqr_plot_filtered)
ggsave("output/Figure_S6.png", plot = average_iqr_plot_filtered, width = 18, height = 18, dpi = 300)
