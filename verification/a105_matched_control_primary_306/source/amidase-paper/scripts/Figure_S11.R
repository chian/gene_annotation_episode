library(ggplot2)
library(reshape2)  # For the melt function


########### CALCULATE AVERAGE SEQUENCE IDENTITY #########
# Read the data file into a dataframe
pid_matrix <- read.table("data/alignment/pid/16_hits_pid.txt", quote="\"")

# Exclude the first column
pid_matrix <- pid_matrix[,-1]

# Set the column names based on the second column
colnames(pid_matrix)[-1] <- pid_matrix$V2

# Convert the dataframe to numeric values
numeric_matrix <- as.matrix(pid_matrix[, -1])
rownames(numeric_matrix) <- pid_matrix$V2

# Create a mask to exclude the diagonal values
mask <- !diag(nrow(numeric_matrix))

# Extract the off-diagonal values
off_diagonal_values <- numeric_matrix[mask]

# Calculate the average of the off-diagonal values
average_identity <- mean(off_diagonal_values)

# Calculate the standard deviation of the off-diagonal values
sd_identity <- sd(off_diagonal_values)

# Output the results
print(paste("Average Identity:", average_identity))
print(paste("Standard Deviation:", sd_identity))
#######################################################################################################

# Melt the matrix
melted_pid_matrix <- melt(pid_matrix)
colnames(melted_pid_matrix)[1] <- "Protein1"
colnames(melted_pid_matrix)[2] <- "Protein2"
colnames(melted_pid_matrix)[3] <- "Identity"

# Convert entries in Protein1 and Protein2 columns to uppercase
melted_pid_matrix$Protein1 <- toupper(melted_pid_matrix$Protein1)
melted_pid_matrix$Protein2 <- toupper(melted_pid_matrix$Protein2)

ggplot(data=melted_pid_matrix, aes(x=Protein1, y=Protein2, fill=Identity)) +
  geom_tile() +
  scale_fill_gradient(low="white", high="blue") +
  labs(title="Protein Identity Matrix", x="", y="") +
  theme_minimal()

##### ordering the identical proteins on a diagonal #########

melted_pid_matrix$Protein1 <- factor(melted_pid_matrix$Protein1, levels = unique(melted_pid_matrix$Protein1))
melted_pid_matrix$Protein2 <- factor(melted_pid_matrix$Protein2, levels = unique(melted_pid_matrix$Protein1))

ggplot(data=melted_pid_matrix, aes(x=Protein1, y=Protein2, fill=Identity)) +
  geom_tile() +
  scale_fill_gradient(low="white", high="blue") +
  labs(title="Protein Identity Matrix", x="", y="") +
  theme_minimal()

######## change the diagonal direction ###########
melted_pid_matrix$Protein2 <- factor(melted_pid_matrix$Protein2, levels = rev(unique(melted_pid_matrix$Protein1)))

# Plot using ggplot
ggplot(data=melted_pid_matrix, aes(x=Protein1, y=Protein2, fill=Identity)) +
  geom_tile() +
  scale_fill_gradient(low="white", high="blue") +
  labs(title="Protein Identity Matrix", x="", y="") +
  theme_minimal()

### adding the percent identity to the cells ####

ggplot(data=melted_pid_matrix, aes(x=Protein1, y=Protein2, fill=Identity)) +
  geom_tile() +
  geom_text(aes(label=sprintf("%.0f", Identity)), size=3, color="black") +  # Display Identity without decimal points
  scale_fill_gradient(low="white", high="blue") +
  labs(title="Protein Identity Matrix", x="", y="") +
  theme_minimal()

### customizing the coloring of the PID matrix
p <- ggplot(data=melted_pid_matrix, aes(x=Protein1, y=Protein2, fill=Identity)) +
  geom_tile() +
  geom_text(aes(label=sprintf("%.0f", Identity)), size=3, color="black") +
  scale_fill_gradientn(colors=c("white", "yellow", "orange", "red"),
                       values = scales::rescale(c(0, 20, 30, 40, 70))) +
  labs( x="", y="") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 90, hjust = 1))
p


ggsave(filename = "output/Figure_S11.png", plot = p, device = "png", width = 6, height = 6, dpi = 300, bg = "white")


