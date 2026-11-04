# Load the required libraries
library("ChemmineR")  # For chemical data processing
library("openxlsx")   # For writing Excel files

##### CHEMICAL FEATURES #####

# Read the SDF (Structure Data File) set containing chemical structures
sdfset <- read.SDFset("data/chemical_descriptors/chemical_structures.sdf")

# Calculate chemical properties and store them in a data frame
propdf <- data.frame(
  MF = MF(sdfset, addH = TRUE),                       # Molecular Formula
  MW = MW(sdfset, addH = FALSE),                      # Molecular Weight
  Ncharges = sapply(bonds(sdfset, type = "charge"), length),  # Number of Charges
  atomcountMA(sdfset, addH = FALSE),                  # Atom Counts
  groups(sdfset, type = "countMA"),                   # Functional Groups
  rings(sdfset, upper = 6, type = "count", arom = TRUE)  # Ring Counts
)

# Write the data frame to an Excel file
write.xlsx(
  propdf,
  file = "data/chemical_descriptors/17_chemical_properties_amidase_substrates.xlsx",
  rowNames = FALSE
)

