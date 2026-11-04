use strict;
my ($work_dir, $analysis_base) = @ARGV;
my $alignment_file = "$work_dir/${analysis_base}.afa";
my $params_to_app = {ref_type => "string"};
    if ($params_to_app->{ref_type} && $params_to_app->{ref_type} ne "none") {
        open(my $afa, '<', $alignment_file) or die "Cannot open $alignment_file: $!";
        my $ref_seq = "";
        my $ref_count = 0;
        while (my $line = <$afa>) {
            chomp($line);
            $line =~ s/#.*//;
            $line =~ s/;.*//;
            $line =~ s/^\s+//;
            $line =~ s/\s+$//;
            next unless length($line);
            if (substr($line, 0, 1) eq ">" && $ref_count > 0) {
                last;
            }
            elsif (substr($line, 0, 1) eq ">") {
                $ref_count++;
                next;
            }
            $ref_seq .= $line;
        }
        close($afa);

        open(my $table, '<', "$work_dir/foma.table") or die "Cannot open $work_dir/foma.table: $!";
        open(my $new_table, '>', "$work_dir/foma2.table") or die "Cannot open $work_dir/foma2.table: $!";
        my $first_line = 1;
        my $pos_count = 0;
        my $spaces_count = 0;
        while (my $line = <$table>) {
            if ($first_line) {
                $first_line = 0;
                print $new_table snp_line_mod($line, "Position in Reference", "Reference Character");
                next;
            }
            my $char = substr($ref_seq, $pos_count, 1);
            $pos_count++;
            if ($char ne "-") {
                my $curr_pos = $pos_count - $spaces_count;
                print $new_table snp_line_mod($line, $curr_pos, $char);
            }
            else {
                print $new_table snp_line_mod($line, "", $char);
                $spaces_count++;
            }
        }
        close($table);
        close($new_table);
        rename "$work_dir/foma2.table", "$work_dir/${analysis_base}.snp.tsv"
            or die "Unable to save SNP table for $analysis_base: $!";
        unlink("$work_dir/foma.table") or warn "Unable to unlink $work_dir/foma.table: $!";
    }
    else {
        rename "$work_dir/foma.table", "$work_dir/${analysis_base}.snp.tsv"
            or die "Unable to save SNP table for $analysis_base: $!";
    }

sub snp_line_mod {
    my($line, $first, $second) = @_;
    chomp($line);
    my @spl = split("\t", $line);
    my $line_str = "";
    my $arr_cnt = 0;
    for my $i (@spl) {
        $line_str = $line_str . "\t" . $i;
        $arr_cnt += 1;
        if ($arr_cnt == 1) {
            $line_str = $line_str . "\t" . $first;
        } elsif ($arr_cnt == 2) {
            $line_str = $line_str . "\t" . $second;
        }
    }
    $line_str =~ s/^\s+//;
    return $line_str . "\n";
}
