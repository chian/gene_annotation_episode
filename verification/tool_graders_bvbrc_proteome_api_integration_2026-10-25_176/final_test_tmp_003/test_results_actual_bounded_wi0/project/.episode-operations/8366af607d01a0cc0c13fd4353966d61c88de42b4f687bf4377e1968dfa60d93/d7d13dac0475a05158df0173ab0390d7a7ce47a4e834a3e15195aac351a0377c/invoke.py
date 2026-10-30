import json,os,sys
r=json.load(open(sys.argv[1]))
os.chdir(r["cwd"])
os.execvpe(r["argv"][0],r["argv"],{**os.environ,**r["environment"]})
