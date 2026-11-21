"""The program the all-vs-all BLAST job runs on its resource: ``python driver.py plan.json``.

Standard library only (like ``blast_preparation_driver``): the job stages this file and its plan beside the query set and
the prepared database archive. It decides nothing: it unpacks the plan's archive (the files ``makeblastdb`` wrote, in
one TAR) into the job's own directory and runs the plan's one argv (``blastp -db ... -query ...``). Its exit status is
the program's; its output is the program's own report file. Exit status 2: the plan is not what this driver reads."""
import json
import subprocess
import sys
import tarfile


def main(argv):
    if len(argv) != 2:
        return 2
    plan = json.load(open(argv[1]))
    with tarfile.open(plan['archive']) as archive:
        archive.extractall('.', filter='data')
    return subprocess.run(plan['argv'], stdin=subprocess.DEVNULL).returncode


if __name__ == '__main__':
    sys.exit(main(sys.argv))
