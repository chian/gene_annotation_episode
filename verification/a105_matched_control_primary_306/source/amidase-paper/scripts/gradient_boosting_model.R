# Clean workspace
rm(list = ls())

# Load required packages
pacman::p_load("tidyverse", "caret", "rsample", "Biostrings",
               "dplyr", "seqinr", "readxl", "DECIPHER", "xgboost",
               "pROC", "doParallel", "openxlsx")

############################
# Load and transform data 
############################

# Read in the substrate-enzyme combinations
rawdat <- read_csv("data/processed/272_enzyme_substrate_combinations.csv") %>%
  mutate(substrate = tolower(substrate))

# Extract list of substrates
substrate <- tolower(rawdat$substrate)

# Read in chemical names and SMILES
allchems <- read.csv("data/machine_learning/amides_smiles.csv", sep = ";")

# Read in chemical properties and merge with chemical names and SMILES
df2 <- read_xlsx("data/chemical_descriptors/17_chemical_properties_amidase_substrates_MW_ring_MW_bond.xlsx")

df3 <- df2 %>%
  bind_cols(allchems) %>%
  mutate(compound = tolower(allchems$compound)) %>%
  filter(compound %in% substrate) %>%
  mutate(smiles = trimws(smiles))

######################################
# Process amino acid sequences
######################################

# Read in amino acid sequences of enzymes with at least one substrate
pnot <- read_xlsx("data/AS_library.xlsx") %>%
  mutate(
    p_notation = toupper(
      case_when(
        grepl("Gord", p_notation) ~ "Gord",
        TRUE ~ p_notation
      )
    )
  ) %>%
  filter(p_notation %in% rawdat$sample_name) %>%
  arrange(p_notation) %>%
  select(p_notation, seq)

# Convert sequences to AAStringSet format
pnot_aa <- AAStringSet(pnot$seq)
names(pnot_aa) <- pnot$p_notation

# Align the sequences
newaln <- AlignSeqs(pnot_aa)
writeXStringSet(newaln, "data/alignment/16_enzyme_substrate_combinations.fasta") # write the alignment to FASTA file   

## identify the start of the AS region first enzyme in the alignment
seqs <- read.alignment("data/alignment/16_enzyme_substrate_combinations.fasta", format = "fasta")  

# Identify the start position of the AS region
tri.pos <- words.pos("grlag",seqs$seq[[1]]) # the AS region of the first enzyme starts with rglag
end.pos <- 160  # Length of the AS region according to Lee et al. (2015)

# Extract AS region from all enzymes in the alignment
nuc <- lapply(as.character(newaln), function(x) substr(x, tri.pos, tri.pos + end.pos))
nucr <- unlist(nuc)
names(nucr) <- names(newaln)
appendf <- data.frame(nams = names(nucr), seq = nucr)

###################################################################
# Convert amino acid sequences to numerical features
###################################################################

# Load the function to convert sequences
source("scripts/convert_seq_5aap.r")

# Convert sequences to list of amino acids
dat_list <- strsplit(appendf$seq, split = "")
names(dat_list) <- appendf$nams

# Convert amino acid sequences to numerical features
extract_feat_list <- lapply(dat_list, convert_seq_5aap)

# Create data frame of features
extract_feat_df <- data.frame(matrix(unlist(extract_feat_list), nrow = length(extract_feat_list), byrow = TRUE), stringsAsFactors = FALSE)
colnames(extract_feat_df) <- paste0("aa", sort(rep(tri.pos:(tri.pos + end.pos), times = 5)), "_", c("polarity", "secondarystruct", "size", "codon_diversity", "charge"))
extract_feat_df$nams <- names(dat_list)

##########################################
# Merge features with substrate data
##########################################

learndat <- extract_feat_df %>%
  left_join(appendf, by = "nams") %>%
  left_join(rawdat, by = c("nams" = "sample_name")) %>%
  left_join(df3, by = c("substrate" = "compound")) %>%
  mutate(id = paste0(nams, "_", substrate)) %>%
  select(-contains("_charge")) %>%  # Remove factor V which explains least variation
  select(-substrate)

##########################################
# Remove features with low variance
##########################################

nozdat <- caret::nearZeroVar(learndat, saveMetrics = TRUE, freqCut = 5, uniqueCut = 2)
which_rem <- rownames(nozdat)[nozdat$nzv == TRUE]

# Remove near-zero variance features
dat <- learndat %>%
  select(-all_of(which_rem)) %>%
  mutate(truth = factor(ifelse(hit_bool == 1, "yes", "no"))) %>%
  select(-hit_bool) %>%
  select(-smiles, -MF, -seq)

################################################
# Split data into training and test sets
################################################

set.seed(123456)

# Split into training (80%) and test (20%) sets
dat_split <- initial_split(dat, strata = "truth", prop = 0.8)
dat_train <- training(dat_split)
dat_test <- testing(dat_split)

# Separate independent variables and dependent variable
x_train <- dat_train %>% select(-nams, -truth, -id)
x_test <- dat_test %>% select(-nams, -truth, -id)
y_train <- dat_train$truth
y_test <- dat_test$truth

# Create data frames for modeling
df_train <- data.frame(x_train, stringsAsFactors = FALSE, row.names = dat_train$id)
df_test <- data.frame(x_test, stringsAsFactors = FALSE, row.names = dat_test$id)

##################################################################################
# Run multiple xgboost models to obtain robust features
##################################################################################

# Define the grid for xgbDART
xgb_grid <- expand.grid(
  nrounds = c(50, 100),
  max_depth = c(3, 6),
  eta = c(0.1, 0.3),
  gamma = c(0, 1),
  colsample_bytree = c(0.7),
  min_child_weight = c(1),
  subsample = c(0.7),
  rate_drop = c(0.1),
  skip_drop = c(0.1)
)

# Register parallel backend
registerDoParallel(cores = parallel::detectCores())

# Function to train xgboost model and extract top features
train_and_extract_features_xgb <- function(seed) {
  set.seed(seed)
  
  xgb_model <- train(
    x = df_train,
    y = y_train,
    method = "xgbDART",
    tuneGrid = xgb_grid,
    trControl = trainControl(method = "repeatedcv", number = 10, repeats = 1, 
                             verboseIter = TRUE, classProbs = TRUE, 
                             savePredictions = "final"),
    verbose = TRUE,
    nthread = parallel::detectCores(),
    tree_method = "hist"
  )
  
  xgb_imp <- varImp(xgb_model, scale = FALSE)
  
  importance_df <- data.frame(
    feature = rownames(xgb_imp$importance),
    importance = xgb_imp$importance[, 1],
    stringsAsFactors = FALSE
  )
  importance_df <- importance_df %>%
    arrange(desc(importance)) %>%
    mutate(rank = row_number()) %>%
    head(50)
  
  return(importance_df)
}

# Train the model 10 times with different seeds and extract top 50 features
seeds <- 1:10
all_top_features_xgb <- lapply(seeds, train_and_extract_features_xgb)

# Combine results into a single data frame
combined_df_xgb <- bind_rows(all_top_features_xgb, .id = "iteration")

# Find features present in at least 70% of the models
common_features_xgb <- combined_df_xgb %>%
  group_by(feature) %>%
  summarize(avg_rank = mean(rank), count = n()) %>%
  filter(count >= 0.7 * length(seeds))

# Save common features to CSV
write_csv(common_features_xgb, "output/machine_learning/common_features_xgboost.csv")

########################################################
# Run final model only with robust features
########################################################

# Filter training and test data to include only common features
common_feature_names_xgb <- common_features_xgb$feature

df_train_filtered_xgb <- df_train[, common_feature_names_xgb, drop = FALSE]
df_test_filtered_xgb <- df_test[, common_feature_names_xgb, drop = FALSE]

# Retrain the model using only the common features
xgb_model_filtered <- train(
  x = df_train_filtered_xgb,
  y = y_train,
  method = "xgbDART",
  tuneGrid = xgb_grid,
  trControl = trainControl(method = "repeatedcv", number = 10, repeats = 3, 
                           verboseIter = TRUE, classProbs = TRUE, 
                           savePredictions = "final"),
  verbose = TRUE,
  nthread = parallel::detectCores(),
  tree_method = "hist"
)

# Save the trained model
saveRDS(xgb_model_filtered, "output/machine_learning/xgboost_final_model.rds")

########################################################
# Evaluate the final model and save results
########################################################

# Generate variable importance plot
xgb_imp_filtered <- varImp(xgb_model_filtered, scale = FALSE)
ggplot(xgb_imp_filtered, top = 50) + 
  xlab("") +
  theme_classic()

# Predict on test set
xgb_pred_filtered <- predict(xgb_model_filtered, newdata = df_test_filtered_xgb)
cm_xgb_filtered <- confusionMatrix(xgb_pred_filtered, y_test)

# Prepare data for export
feature_importance_xgb <- data.frame(Feature = rownames(xgb_imp_filtered$importance), Overall = xgb_imp_filtered$importance$Overall)

# Prepare confusion matrix by class
cm_xgb_filtered_byClass <- as.data.frame(cm_xgb_filtered$byClass)
cm_xgb_filtered_byClass$Metric <- rownames(cm_xgb_filtered_byClass)
cm_xgb_filtered_byClass <- cm_xgb_filtered_byClass[, c("Metric", setdiff(names(cm_xgb_filtered_byClass), "Metric"))]

# Save the ROC plot as an image
roc_plot_path <- "output/machine_learning/roc_plot.png"
xgb_prob <- predict(xgb_model_filtered, newdata = df_test_filtered_xgb, type = "prob")
xgb_roc <- roc(response = ifelse(y_test == "no", 0, 1), predictor = xgb_prob[, "yes"], plot = TRUE, ci = TRUE)
png(roc_plot_path)
plot(xgb_roc, type = "s", col = "#529DCF", xaxs = "i", yaxs = "i", print.auc = TRUE, print.auc.x = 0.8, print.auc.y = 0.8, xlim = c(0.5,0), ylim = c(0,1.1))
dev.off()

# Create an Excel workbook and add the feature importance and confusion matrix
wb <- createWorkbook()
addWorksheet(wb, "FeatureImportance")
addWorksheet(wb, "ConfusionMatrixByClass")
addWorksheet(wb, "AUC")

writeData(wb, sheet = "FeatureImportance", feature_importance_xgb)
writeData(wb, sheet = "ConfusionMatrixByClass", cm_xgb_filtered_byClass)

# Insert the ROC plot into the workbook
insertImage(wb, sheet = "AUC", file = roc_plot_path, width = 6, height = 4, startRow = 1, startCol = 1)

# Save the workbook
saveWorkbook(wb, file = "output/machine_learning/xgboost_results.xlsx", overwrite = TRUE)
