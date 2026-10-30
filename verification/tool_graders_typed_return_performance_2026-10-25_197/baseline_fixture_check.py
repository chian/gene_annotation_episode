import os, pathlib, sys
own=pathlib.Path(__file__).resolve().parent
baseline=own/"baseline_candidate"
os.chdir(baseline)
sys.path.insert(0,str(baseline))
import pytest
print("Exact1045-path frozen186 source plus same seven retained fixtures:",baseline,flush=True)
sys.exit(pytest.main(["-q","-p","no:cacheprovider","tests/test_form_reference_validation.py::test_public_genome_resolvers_reuse_facts_but_preserve_possession_and_semantics","--basetemp="+str(own/"baseline_fixture_001/temporary"),"--junitxml="+str(own/"baseline_fixture_001/tests.xml")]))
