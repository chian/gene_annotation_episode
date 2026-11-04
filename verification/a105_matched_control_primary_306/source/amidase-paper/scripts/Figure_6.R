## alluvial plot with hits
###############################

library(ggplot2)
library(ggalluvial)
library(dplyr)
library(magrittr)
library(reshape2)
library(tidyverse)
library(viridis)
library(readxl)

dat <- read_excel("data/GMGC_distribution_16_hits.xlsx") %>%
  select(-'original seq') %>%
  mutate(enzyme = paste0(toupper(shorthand), " [", Genus, "]")) %>%
  rowwise() %>%
  mutate(human_total = sum(c_across(contains("human")), na.rm = TRUE)) %>%
  ungroup() %>%
  select(-contains("human"), human_total) %>%
  rowwise() %>%
  mutate(animal_total = sum(c_across(c("dog-gut", "cat-gut", "mouse-gut", "pig-gut", "animal gut")), na.rm = TRUE)) %>%
  ungroup() %>%
  rowwise() %>%
  mutate(aquatic_total = sum(c_across(c("marine", "freshwater")), na.rm = TRUE)) %>%
  ungroup() %>%
  select(-contains("human"), -contains("gut"), -contains("marine"), -contains("freshwater"), human_total, animal_total, aquatic_total) %>%
  select(-other)

dat2 <- dat

# Rename columns
names(dat2)[names(dat2) == "human_total"] <- "human"
names(dat2)[names(dat2) == "animal_total"] <- "animal"
names(dat2)[names(dat2) == "aquatic_total"] <- "aquatic"

# Replace NA entries with 0
dat2[is.na(dat2)] <- 0

long_df <- melt(dat2)
# Filter the data to show only alluviums with values greater than 3
long_df_filtered <- long_df %>% filter(value > 3)

### plot alluvial plot  with percentages
p <- ggplot(data = long_df_filtered, 
            aes(y = value, axis1 = enzyme, axis2 = variable)) +
  geom_alluvium(aes(fill = enzyme), alpha = 0.8, width = 0.1) +
  geom_stratum(width = 0.4) +
  geom_text(stat = "stratum", aes(label = paste0(after_stat(stratum), ": ", after_stat(count), " (", round(after_stat(prop) * 100, 1), "%)")), size = 4) +
  scale_fill_viridis_d(option = "viridis") +
  theme_void() +
  theme(legend.position = "none")

p

ggsave("output/Figure_S13A.png", plot = p, width = 12, height = 12, dpi = 600)

#### only environmental habitats ###
dat3 <- dat2 %>%
  select(-human, -animal)

p <- ggplot(data = long_df, 
            aes(y = value, axis1 = enzyme, axis2 = variable)) +
  geom_alluvium(aes(fill = enzyme), alpha = 0.8, width = 0.1) +
  geom_stratum(width = 0.35) +
  geom_text(
    stat = "stratum", 
    aes(label = ifelse(after_stat(count) > 3, 
                       paste0(after_stat(stratum), ": ", after_stat(count), 
                              " (", round(after_stat(prop) * 100, 1), "%)"), 
                       "")), 
    size = 3.5
  ) +
  scale_fill_viridis_d(option = "viridis") +
  theme_void() +
  theme(legend.position = "none")

p

# Save the plot
ggsave("output/Figure_6.png", plot = p, width = 12, height = 8, dpi = 600)

### only the most promiscuous enzymes ###
subset_df <- long_df %>%
  filter(grepl("P131|P148|P162", enzyme))

p <- ggplot(data = subset_df, 
            aes(y = value, axis1 = enzyme, axis2 = variable)) +
  geom_alluvium(aes(fill = enzyme), alpha = 0.8, width = 0.1) +
  geom_stratum(width = 0.4) +
  geom_text(stat = "stratum", aes(label = paste0(after_stat(stratum), ": ", after_stat(count), " (", round(after_stat(prop) * 100, 1), "%)")), size = 3.5) +
  scale_fill_viridis_d(option = "viridis") +
  theme_void() +
  theme(legend.position = "none")

p

ggsave("output/Figure_S13B.png", plot = p, width = 12, height = 8, dpi = 600)
