from __future__ import print_function

import sys
import os

def report_error(error_message, overwrite=False):

    user_path = os.getenv("P3_USER_ERROR_DESTINATION")
    if user_path is None:
        return

    try:
        if overwrite:
            mode="w"
        else:
            mode="a"
        fh = open(user_path, mode)
        print(error_message, file=fh)
        fh.close()
    except Exception as e:
        print("error report to %s failed: %s" % (user_path, e), file=sys.stderr)
        
