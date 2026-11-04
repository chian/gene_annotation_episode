#!/usr/bin/env python
import argparse
import sys
from p3_error_reporting import report_error

from sra_tools import download_sra_data

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='A script to gather SRA data for a given accession id.',
                usage='usage: ./p3_sra.py -bin <path to fasterq-dump> --out <fastq output directory> --id <SRA accession id (SRX, SRP, SRR, DRX, DRP, DRR, ERR, ERX, ERP)>')

    parser.add_argument('--bin', required=False, help='Path to the fasterq-dump binary', default="fasterq-dump")
    parser.add_argument('--out', required=False, help='Temporary output directory for fastq files')
    parser.add_argument('--id', required=True, help='SRA accession id (SRX, SRP, SRR)')
    parser.add_argument('--metaonly', action='store_true', help='Skip the download of the fastq files')
    parser.add_argument('--metadata-file', help='Store the metadata in the given file')
    parser.add_argument('--sra-metadata-file', help='Store the original SRA metadata XML in the given file')
    parser.add_argument('--gzip', action='store_true', help='Compress the fastq files after download')

    args = parser.parse_args()

    if not args.metaonly and not args.out:
        sys.exit("Output directory must be specified")

    accession_id = args.id
    acceptable_prefixes = ('SRX', 'SRP', 'SRR', 'DRX', 'DRP', 'DRR', 'ERR', 'ERX', 'ERP')
    if accession_id.startswith(acceptable_prefixes):
        download_sra_data(args.bin, args.out, accession_id, args.metaonly, args.gzip, args.metadata_file, args.sra_metadata_file)
    else:
        err = 'Accession ID must start with: ' + ', '.join(acceptable_prefixes)
        report_error(err);
        sys.exit(err)
