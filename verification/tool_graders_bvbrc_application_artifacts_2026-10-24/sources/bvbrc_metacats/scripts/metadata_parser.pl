############################
# Written by: Brett Pickett at JCVI (May 2016)
# Modified by: Jacob Porter at UVa (Summer 2021)
# Input 1: multiple sequence alignment in fasta format and
# Input 2 TSV file with ID (matching fasta header) in first column and each metadata category in additional columns
# Output 1: meta-CATS Goodness of Fit test results for each metadata category
# Output 2: meta-CATS Test of Independence results for each metadata category
# Output 3: ID-metadata-sequence input file required for meta-CATS (for each metadata category)
# Output 4: Summary table showing number of significant sequence positions for each metadata category and for the combination of all categories
############################
#!/usr/bin/perl
use strict;
use warnings;
use File::Basename;
use IPC::Run qw(run);
# use Statistics::R;

my ($seqFile, $metaDataFile, $seqType, $pvalue, $check_header, $outputDir) = @ARGV;

# my $metaDataFile = 'metadata.tsv';
# my $seqFile = 'input.afa'; #aligned sequences

print STDOUT "MetaCATS metadata parser. Sequence type: $seqType.\n";

my %categories;
my $lineNum = 0;
my $numCategories = 0;
my @headers;
my @data;
my @fileNames;

# Get the first line of the metadata file to detect if it is a header line.
if ($check_header) {
	open (METADATA, "<$metaDataFile") || die "$metaDataFile: $!\n";
	my $line = <METADATA>;
	$line =~ s/\r\n/\n/g;
	chomp $line;
	@data=split /\t/,$line;
	close (METADATA);

	# Search the seqs file to see if the metadata file has a header line.
	open (SEQS, "<$seqFile") || die "$seqFile: $!\n"; 	#check to see if file exists
		while(my $String = <SEQS>)
		{
			if(rindex($String, ">", 0) == 0 && $String =~ /$data[0]/)
			{
				@headers = ("0");
				my $line_len = scalar(@data);
				for (my $i = 1; $i < $line_len; $i++) {
					push(@headers, "Category_" . $i);
				}
				$lineNum = 1;
				$numCategories = @headers;
				last;
			}
		}
	close(SEQS);
}

#load metadata into hash
open (METADATA, "<$metaDataFile") || die "$metaDataFile: $!\n";  #check to see if file exists
print "Loading Metadata...\n";

while (my $line = <METADATA>) {     #read all lines of the file
	$line =~ s/\r\n/\n/g;
	chomp $line;
	if($lineNum ==1){ # read metadata lines and automatically populate 2D-hash`
		@data=split /\t/,$line;
		for (my $i = 1; $i < $numCategories; $i++){
			$categories{$data[0]}{$headers[$i]} = $data[$i]; #1D = seqID, 2D = metadata category, value = attribute
		}
	}
	elsif ($lineNum == 0){ #read header line and count number of metadata categories
		chomp $line;
		$lineNum = 1;
		@headers=split /\t/,$line;
		$numCategories = @headers;
	}
}
close (METADATA);

# read in sequence data and store in same hash as metadata
open (SEQS, "<$seqFile") || die "$seqFile: $!\n"; 	#check to see if file exists
my $tempName;
print "Loading Sequence Data...\n";

while (my $line1 = <SEQS>) {		#read all lines of the file
	$line1 =~ s/\r\n/\n/g;
	chomp $line1;
	if ($line1 =~m/^>(\S+)/){
		$tempName = $1;
		#print "$tempName\n";
	}
	else {
		$categories{$tempName}{Seq} .= $line1;
	}
}
close (SEQS);

#add 1 space between each sequence letter to format for downstream analysis
foreach my $outer (keys %categories) {
	if (exists $categories{$outer}{Seq}){
		$categories{$outer}{Seq} = join(" ",split(//,$categories{$outer}{Seq}));
		my $space = ' ';
		$categories{$outer}{Seq} = $space.$categories{$outer}{Seq};
	}
}

# calculate number of different fields for each category
my %categoryCounts;
for (my $k = 1; $k < $numCategories; $k++){
	foreach my $outer (keys %categories) {
		$categoryCounts{$headers[$k]}{$categories{$outer}{$headers[$k]}}++;
	}
}


#assign group numbers in new hash
my %assignments;
my %rev_assignments;
my @sortedOuter = sort keys %categoryCounts;
my $outerLength = @sortedOuter;
my @sortedInner;
my $innerLength;
my $number = 1;
foreach my $outer2 (@sortedOuter){
	@sortedInner = sort keys %{$categoryCounts{$outer2}};
	$innerLength = @sortedInner;
	$number = 1;
	foreach my $inner2 (@sortedInner) {
		# print STDOUT "Assignments: $outer2 $inner2 $number\n";
		$assignments{$outer2}{$inner2}= $number;
		$rev_assignments{$outer2}{$number}= $inner2;
		$number++;
	}
}

# construct separate output files for each category and sequence
my %file_to_category;
foreach my $category1 (@sortedOuter){#metadata category
	push(@fileNames, "$outputDir/$category1.txt");
	$file_to_category{"$outputDir/$category1.txt"} = $category1;
	open (OUTFILE, ">$outputDir/$category1.txt") || die "$category1.txt: $!\n";
	my @seqLabels = sort keys %categories;
	foreach my $seq1 (@seqLabels){
		my $attribute = $categories{$seq1}{$category1}; #points to numerical assignment representing metadata attribute
		#Only output the label, category, and sequence for labels that have BOTH category AND sequence data
		if(exists $categories{$seq1}{Seq}){
		#	#print "present: $seq1\n";
			print OUTFILE "$seq1\t$assignments{$category1}{$attribute}\t$categories{$seq1}{Seq}\n";
		}
		else{
		#	#print "absent: $seq1\n";
			next;
		}
	}
	close (OUTFILE);
}

#Create a communication bridge with R and start R to run meta-CATS code (in R)
# my @results;
# my $R = Statistics::R->new();
print "Running Statistics...\n";
foreach my $file1 (@fileNames){#metadata category
	my $category = $file_to_category{$file1};
	my $num_hash = $rev_assignments{$category};
	my $group_count = keys %$num_hash;
	print STDOUT "Category $category $group_count\n";
	open (MSAFILE, "<$file1") || die "$file1: $!\n";
	my $boolean1 = 0;
	my $firstloop = 0;
	my $oldCategoryNum = 0;
	while (my $line1 = <MSAFILE>) {		#read all lines of the file
		chomp $line1;
		if ($line1 =~m/^.+?\t(.+)?\t.+/){
			my $newCategoryNum = $1;
			if ($firstloop == 0){
				$oldCategoryNum = $newCategoryNum;
				$firstloop = 1;
			}
			elsif ($oldCategoryNum != $newCategoryNum){
				$boolean1 = 1;
			}
			elsif ($oldCategoryNum == $newCategoryNum){
				next
			}
		}
	}
	close (MSAFILE);
	if($boolean1 == 1){
		print "\t$file1\n";
		my $base = basename($file1);
		$base = substr($base, 0, length($base) - 4);
		my $ok = run("Meta-CATS", $file1, $seqType, $pvalue, $outputDir, $base);
		if (!$ok)
		{
			die "Running Meta-CATS.R failed.";
		}
		copy_to_tsv($outputDir, "$base-chisqTable", $pvalue);
		use_group_string_chisq($outputDir, "$base-chisqTable", $group_count, $num_hash);
    	copy_to_tsv($outputDir, "$base-mcTable", $pvalue);
		use_group_string_mcTable($outputDir, "$base-mcTable", $num_hash);
		unlink("$outputDir$base-chisqTable.txt") or warn "Unable to unlink $!";
		unlink("$outputDir$base-mcTable.txt") or warn "Unable to unlink $!";
		# $R->set('inFilename', $file1);
		# my $Rrun1 = $R->run_from_file("chisq_ViPR-perl_BEP.R");
		# my $returnedFilename = $R->get('outfilename1');
		# push(@results, "$returnedFilename");
	}
	elsif($boolean1 == 0){
		next;
	}
}

sub use_group_string_chisq {
	my ($work_dir, $basename, $group_count, $num_hash_ref) = @_;
	my $temp_path = "$work_dir$basename.temp.tsv";
	my $path = "$work_dir$basename.tsv";
	open my $fh, '<', $temp_path or die "Cannot open $temp_path: $!";
    open(IN, '>', $path) or die "Cannot open $path: $!";
	# Convert groups column numbers to group strings. Change the column header from residue diversity to column headers for group strings.
	print IN "Position\tChi-square_value\tP-value\tDegrees_of_freedom\tFewer_5";
	for (my $i = 1; $i <= $group_count; $i ++) {
		my $header_str = %$num_hash_ref{$i};
		if (!$header_str) {
			$header_str = "Unlabeled";
		} else {
			# Extract substring after the last "/"
			$header_str =~ s{.*/}{};
		}
        print IN "\t" . $header_str;
		# print IN "\t" . %$num_hash_ref{$i};
	}
	print IN "\n";
	while (my $line = <$fh>) {
		chomp $line;
		my @columns = split(/\t/, $line);
		my %line_group;
		for (my $i = 1; $i <= $group_count; $i ++) {
			$line_group{$i} = "";
		}
		my $groups_str = pop(@columns);
		if (substr($groups_str, 0, 2) eq "gr") {
			$groups_str =~ s/\|/\t/g;
			my @groups = split("\t", $groups_str);
			for my $g_string (@groups) {
				$g_string =~ /group([0-9]+)\((.*)\)/;
				$line_group{$1} = $2;
			}
		}
		for (my $i = 1; $i <= $group_count; $i ++) {
			push(@columns, $line_group{$i});
		}
		print IN join("\t", @columns) . "\n";
	}
	unlink($temp_path) or warn "Unable to unlink $!";
}

sub use_group_string_mcTable {
	my ($work_dir, $basename, $num_hash_ref) = @_;
	my $temp_path = "$work_dir$basename.temp.tsv";
	my $path = "$work_dir$basename.tsv";
	open my $fh, '<', $temp_path or die "Cannot open $temp_path: $!";
    open(IN, '>', $path) or die "Cannot open $path: $!";
	print IN "Position\tMultiple_comparison_p-value\tGroups\n";
	my $sel = 1;
	# Convert group numbers to group strings.
	while ( my $line = <$fh> ) {
        chomp $line;
        my @columns = split(/\t/, $line);
		my $groups_str = $columns[-1];
		my @groups = split(',', $groups_str);
		my $text = "";
		for my $num (@groups) {
			my $group_str = %$num_hash_ref{$num};
			if (!$group_str) {
				$group_str = "Unlabeled";
			} else {
				 # Extract substring after the last "/"
				 $group_str =~ s{.*/}{};
			}
			$text = $text . $group_str . ',';
		}
		while (substr($text, 0, 1) eq ",") {
			$text = substr($text, 1);
		}
		if (length($text) > 1) {
			$text = substr($text, 0, -1);
		}
		print IN join("\t", @columns[0..$sel])."\t".$text."\n";
	}
	unlink($temp_path) or warn "Unable to unlink $!";
}

sub copy_to_tsv {
    my($work_dir, $basename, $pvalue) = @_;
    my $filename = "$work_dir$basename.txt";
    my $path = "$work_dir$basename.temp.tsv";
    open my $fh, '<', $filename or die "Cannot open $filename: $!";
    open(IN, '>', $path) or die "Cannot open $path: $!";
    my $sel = 0; # Location of p-value.
    my $stuff = "\t"; # Delimiter for final columns.
    if (substr($basename, length($basename) - 7) eq "mcTable") {
        $sel = 1;
        $stuff = ",";
    } else {
        $sel = 2;
    }
    my $count = 0;
    while ( my $line = <$fh> ) {
        next if(length($line) <= 1);
        if (substr($line, 0, 1) eq "\"") {
            next;
        }
        chomp $line;
        $count = $count + 1;
        my @columns = split(/\t/, substr($line, 5));
        # Remove whitespace and some formatting from columns.
        for ( my $i = 0; $i < scalar(@columns); $i++ ) {
            my $thing = $columns[$i];
            $thing=~ s/^\s+|\s+$//g;
            if ($i == scalar(@columns) - 1) {
                $thing =~ s/_/\x20/g;
            }
            @columns[$i] = $thing;
        }
        # Add a column if the position is statistically significant or not.
        my $obs_p_value = $columns[$sel];
        if ($obs_p_value ne "NA" and $obs_p_value < $pvalue) {
			my $final = join($stuff, map { defined($_) ? $_ : '' } @columns[$sel+1..scalar(@columns)]);
        	$final =~ s/[,|\t]$//;
			# Join the columns together and print the results in a TSV file.
        	print IN join("\t", @columns[0..$sel])."\t".$final."\n";
        }
    }
    close(IN);
    close($fh);
    return $count;
}

# #Parse all results files and save summaries of those that have highest number of significant positions
# print "Parsing Results...\n";
# open (SUMMARY, ">AA_Summary_Results-$metaDataFile.txt") || die "AA_Summary_Results-$metaDataFile.txt: $!\n";
# open (RESULTSALL, ">1AA_Summary_Results_ALL-$metaDataFile.txt") || die "AA_Summary_Results_ALL-$metaDataFile.txt: $!\n";
# print SUMMARY "Category Counts\nMetadata Category\t# Significant Positions\t# Total Positions\t% for each Category (# Sig / # Total )\n";
# print RESULTSALL "Position	Chi-Square Score	P-Value	Degrees of Freedom	Sparse Table (i.e. <5 of any residue)	Residue Diversity Between Groups\tResults_Filename\n";
# my %resultsStats;
# my @resultsArray;
# my $resultsLength = @results;
# my $numSigResults =0;
# for (my $p = 0; $p < $resultsLength; $p++){#metadata category
# 	open (RESULTSDATA, "<$results[$p]") || die "$results[$p]: $!\n";
# 	print "\t$results[$p]...\n";
# 	while (my $line4 = <RESULTSDATA>) {     #read all lines of the file
# 		chomp $line4;
# 		if ($line4=~m/^ .+/){
# 			@resultsArray=split /\t/,$line4;
# 			$resultsArray[0] =~ s/^\s+|\s+$//g;
# 			$resultsArray[2] =~ s/^\s+|\s+$//g;
# 			if($resultsArray[2] <= 0.05){
# 				$resultsStats{$results[$p]}{sig}++;
# 				print RESULTSALL "$line4\t$results[$p]\n";
# 			}
# 		}
# 		else{
# 			next;
# 		}
# 		$resultsStats{$results[$p]}{total}++;
# 	}
# 	my $quotient;
# 	if(defined $resultsStats{$results[$p]}{sig}){
# 		$quotient = 100*($resultsStats{$results[$p]}{sig}/$resultsStats{$results[$p]}{total});
# 		$numSigResults += $resultsStats{$results[$p]}{sig};
# 		print SUMMARY "$sortedOuter[$p]\t$resultsStats{$results[$p]}{sig}\t$resultsStats{$results[$p]}{total}\t";
# 		printf SUMMARY ("%.1f",$quotient);
# 		print SUMMARY "%\n";
# 	}
# 	else{
# 		print SUMMARY "$sortedOuter[$p]\tNone\tNA\n";
# 	}
# 	close (RESULTSDATA);
# }
# my @percValues;
# #add all significant sites for each category and calculate percentages for each
# print SUMMARY "\nComprehensive Counts:\nMetadata Category\t# Significant Positions in Single Category\t# Significant Positions from ALL Categories\tPercentage for ALL Categories\n";
# for (my $q = 0; $q < $resultsLength; $q++){#metadata category
# 	if(defined $resultsStats{$results[$q]}{sig}){
# 		print SUMMARY "$sortedOuter[$q]\t$resultsStats{$results[$q]}{sig}\t$numSigResults\t";
# 		$resultsStats{$results[$q]}{totalPerc} = 100*($resultsStats{$results[$q]}{sig}/$numSigResults);
# 		$resultsStats{$results[$q]}{totalPerc} = sprintf "%.1f", $resultsStats{$results[$q]}{totalPerc};
# 		print SUMMARY "$resultsStats{$results[$q]}{totalPerc} %\n";
# 		push(@percValues, "$resultsStats{$results[$q]}{totalPerc}");
# 	}
# }
# close (SUMMARY);
# $R->set('lbls', \@sortedOuter);
# $R->set('slices', \@percValues);
# $R->set('inFilename3', $metaDataFile);
# # my $Rrun2 = $R->run_from_file("pieChart.R");
# $R->stop();

# print "Complete\n";
# print "Number of significant results for each metadata category can be found in:\n\"AA_Summary_Results-$metaDataFile\"\n\n";
# # print "Pie chart of results can be found in:\n\"AA-$metaDataFile-PieChart.pdf\"\n";
