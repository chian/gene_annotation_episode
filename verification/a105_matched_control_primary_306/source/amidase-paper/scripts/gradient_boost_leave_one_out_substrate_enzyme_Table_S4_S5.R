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

########################################################
######## LEAVE ONE COMPOUND OUT  #######################
########################################################

# Extract the compounds from the 'id' column
cmpnds <- unique(word(dat$id, sep = "_", 2))

# Create empty lists to store results
by_class_metrics_list <- list()
feature_importance_list <- list()  # List to store feature importance

set.seed(123)

# Define the grid for xgbDART
xgb_grid <- expand.grid(
  nrounds = c(50, 100),  # fewer boosting iterations
  max_depth = c(3, 6),
  eta = c(0.1, 0.3),  # learning rate
  gamma = c(0, 1),
  colsample_bytree = c(0.7),
  min_child_weight = c(1),
  subsample = c(0.7),
  rate_drop = c(0.1),  # specific to DART
  skip_drop = c(0.1)   # specific to DART
)

# Loop through each compound and leave it out for testing
for (i in 1:length(cmpnds)) {
  
  # Identify compound to be 'left out'
  loo_cmpnd <- cmpnds[i]
  
  # Leave one compound out for training
  dat_train <- dat[!grepl(loo_cmpnd, dat$id),]
  
  # Select the left-out compound for testing
  dat_test <- dat[grepl(loo_cmpnd, dat$id),]
  
  print(paste("Training without compound:", loo_cmpnd))
  
  # Independent variables
  x_train <- dat_train[, !colnames(dat_train) %in% c("nams", "truth", "id")]
  x_test <- dat_test[, !colnames(dat_test) %in% c("nams", "truth", "id")]
  
  # Dependent variable
  y_train <- dat_train$truth
  y_test <- dat_test$truth
  
  # Make a data frame for prediction
  df_train <- data.frame(x_train, stringsAsFactors = FALSE, row.names = dat_train$id)
  df_test <- data.frame(x_test, stringsAsFactors = FALSE, row.names = dat_test$id)
  
  # XGBoost training
  xgb_model <- train(
    x = df_train,
    y = y_train,
    method = "xgbDART",
    tuneGrid = xgb_grid,
    trControl = trainControl(method = "repeatedcv", number = 10, repeats = 3, 
                             verboseIter = TRUE, classProbs = TRUE, 
                             savePredictions = "final"),
    verbosity = 0,
    nthread = parallel::detectCores(),
    tree_method = "hist"
  )
  
  # Testing set prediction for xgbDART
  xgb_pred <- predict(xgb_model, newdata = df_test)
  cm_xgb <- confusionMatrix(xgb_pred, as.factor(y_test))
  
  # Store prediction results for the compound
  by_class_metrics <- as.data.frame(t(cm_xgb[["byClass"]]))
  by_class_metrics <- by_class_metrics[, c("Precision", "Recall", "F1", "Balanced Accuracy")]
  by_class_metrics$Compound <- loo_cmpnd  # Add the compound name
  
  # Append to list
  by_class_metrics_list[[loo_cmpnd]] <- by_class_metrics
  
  # Get feature importance
  importance <- varImp(xgb_model)$importance
  importance$Feature <- rownames(importance)
  importance <- importance[order(-importance$Overall), ]
  importance$Compound <- loo_cmpnd  # Add the compound name
  
  # Append to feature importance list
  feature_importance_list[[loo_cmpnd]] <- importance
  
  print(paste("Metrics and feature importance stored for", loo_cmpnd))
}

# Combine byClass metrics for all compounds into a dataframe
by_class_metrics_df <- bind_rows(by_class_metrics_list)

# Combine feature importance data frames
feature_importance_df <- bind_rows(feature_importance_list)

# Save prediction results and feature importance to Excel file
wb <- createWorkbook()
addWorksheet(wb, "Metrics")
addWorksheet(wb, "Feature Importance")
writeData(wb, sheet = "Metrics", by_class_metrics_df)
writeData(wb, sheet = "Feature Importance", feature_importance_df)
saveWorkbook(wb, file = "output/leave_one_compound_out_results.xlsx", overwrite = TRUE)

######################################################
####### LEAVE ONE ENZYME OUT #########################
######################################################

# Extract the enzymes from the 'id' column
enzymes <- unique(word(dat$id, sep = "_", 1))  # Extract the enzyme part

# Create empty lists to store results
by_class_metrics_list <- list()
feature_importance_list <- list()  # List to store feature importance

# Set random seed
set.seed(123)

# Loop through each enzyme and leave it out for testing
for (i in 1:length(enzymes)) {
  
  # Identify enzyme to be 'left out'
  loo_enzyme <- enzymes[i]
  
  # Leave one enzyme out for training
  dat_train <- dat[!grepl(loo_enzyme, dat$id),]
  
  # Select the left-out enzyme for testing
  dat_test <- dat[grepl(loo_enzyme, dat$id),]
  
  print(paste("Training without enzyme:", loo_enzyme))
  
  # Independent variables
  x_train <- dat_train[, !colnames(dat_train) %in% c("nams", "truth", "id")]
  x_test <- dat_test[, !colnames(dat_test) %in% c("nams", "truth", "id")]
  
  # Dependent variable
  y_train <- dat_train$truth
  y_test <- dat_test$truth
  
  # Make a data frame for prediction
  df_train <- data.frame(x_train, stringsAsFactors = FALSE, row.names = dat_train$id)
  df_test <- data.frame(x_test, stringsAsFactors = FALSE, row.names = dat_test$id)
  
  # XGBoost training
  xgb_model <- train(
    x = df_train,
    y = y_train,
    method = "xgbDART",
    tuneGrid = xgb_grid,
    trControl = trainControl(method = "repeatedcv", number = 10, repeats = 3, 
                             verboseIter = TRUE, classProbs = TRUE, 
                             savePredictions = "final"),
    verbosity = 0,
    nthread = parallel::detectCores(),  # Use all available CPU cores
    tree_method = "hist"  # Efficient tree construction on CPU
  )
  
  # Testing set prediction for xgbDART
  xgb_pred <- predict(xgb_model, newdata = df_test)
  cm_xgb <- confusionMatrix(xgb_pred, as.factor(y_test))
  
  # Store cm_xgb[["byClass"]] results for the enzyme
  by_class_metrics <- as.data.frame(t(cm_xgb[["byClass"]]))
  by_class_metrics <- by_class_metrics[, c("Precision", "Recall", "F1", "Balanced Accuracy")]
  by_class_metrics$Enzyme <- loo_enzyme  # Add the enzyme name
  
  # Append to list
  by_class_metrics_list[[loo_enzyme]] <- by_class_metrics
  
  # Get feature importance
  importance <- varImp(xgb_model)$importance
  importance$Feature <- rownames(importance)
  importance <- importance[order(-importance$Overall), ]
  importance$Enzyme <- loo_enzyme  # Add the enzyme name
  
  # Append to feature importance list
  feature_importance_list[[loo_enzyme]] <- importance
  
  print(paste("Metrics and feature importance stored for", loo_enzyme))
}

# Combine byClass metrics for all enzymes into a dataframe
by_class_metrics_df <- bind_rows(by_class_metrics_list)

# Combine feature importance data frames
feature_importance_df <- bind_rows(feature_importance_list)

# Save prediction results and feature importance to Excel file
wb <- createWorkbook()
addWorksheet(wb, "Metrics")
addWorksheet(wb, "Feature Importance")
writeData(wb, sheet = "Metrics", by_class_metrics_df)
writeData(wb, sheet = "Feature Importance", feature_importance_df)
saveWorkbook(wb, file = "output/leave_one_enzyme_out_results.xlsx", overwrite = TRUE)