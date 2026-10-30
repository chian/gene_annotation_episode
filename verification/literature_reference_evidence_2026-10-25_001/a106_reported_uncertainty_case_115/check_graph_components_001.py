"""One explicitly nominated retained-figure analysis; not a production reader.

Source pixel coordinates/roles and +/-1px reading choices are analyst selections.
The calculation does not infer axes, experiments, statistical independence,
confidence intervals or causal attribution. Original image bytes are read only.
"""
from pathlib import Path
from itertools import product
from math import sqrt
import hashlib,json
from PIL import Image
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
IMAGE=ROOT/'research/experimental_scoring_review_2026-10-23/a106_perturbation_sheet_013/raw/PMC4664914_figure6.jpg'
raw=IMAGE.read_bytes()
with Image.open(IMAGE) as im: image_metadata={'width':im.width,'height':im.height,'mode':im.mode}
# Exact displayed raw-CFU axis tick labels, with nominated pixel centers.
# All coordinates apply ONLY to Fig6B's right-hand120h panel.
selected={'lower_axis_y':807.0,'upper_axis_y':551.0,
          'W_mean_y':671.5,'K_mean_y':730.5,'R_mean_y':669.5,
          'W_upper_sd_y':659.5,'K_upper_sd_y':712.0,'R_upper_sd_y':657.5}
def measure(recipe):
 def value(y):return 10**(6+3*(recipe['lower_axis_y']-y)/(recipe['lower_axis_y']-recipe['upper_axis_y']))
 means={r:value(recipe[r+'_mean_y']) for r in 'WKR'}
 sds={r:value(recipe[r+'_upper_sd_y'])-means[r] for r in 'WKR'}
 ses={r:sds[r]/sqrt(3) for r in 'WKR'}
 W,K,R=(means[r] for r in 'WKR');D=W-K;F=(R-K)/D
 return {'means_CFU_per_mL':means,'reported_SD_CFU_per_mL_graph_reading':sds,
         'derived_mean_SE_CFU_per_mL':ses,
         'components':{'perturbation_difference':D,'symmetric_effect':D/(W+K),
                       'restoration_fraction_raw':F,'restoration_agreement':max(0,min(1,1-abs(R-W)/abs(D)))},
         'difference_variance_bounds_unknown_cross_arm_covariance':[(ses['W']-ses['K'])**2,(ses['W']+ses['K'])**2]}
point=measure(selected)
choices=[]
for shifts in product((-1.0,1.0),repeat=len(selected)):
 recipe={k:v+d for (k,v),d in zip(selected.items(),shifts)}
 choices.append(measure(recipe))
def ranges(path):
 vals=[]
 for row in choices:
  for key in path:row=row[key]
  vals.append(row)
 return [min(vals),max(vals)]
report={'evidence_class':'graph-derived conditional120h CFU-density reading; no production grader/model/statisticalconfidence proof',
 'source_image':str(IMAGE.relative_to(ROOT)),'image_sha256':hashlib.sha256(raw).hexdigest(),'image':image_metadata,
 'panel':'Figure6B,120h','actual_roles':{'W':'wild-type+pBAD18empty','K':'delta-yeaG+pBAD18empty','R':'delta-yeaG+pBAD18-yeaG'},
 'endpoint':'arithmetic mean colony-forming units per mL at120h sustained Nstarvation, as displayed; not a normalized survival probability',
 'axis':'raw CFU/mL on log10 display; labelled1e6 at y807 and1e9 at y551',
 'selected_pixel_recipe':selected,'pixel_recipe_status':'analyst-nominated line centers after inspecting original figure; not paper-reported numerical means',
 'point':point,'reported_spread_type':'SD','reported_count':3,
 'repetition_support':'main Methods says mean averages of3 independent experiments or more unless specified; Fig6B specifies n3',
 'unknowns':['arm-pairing/block identities','cross-arm covariance','cross-time covariance','raw colony counts/dilutions/plated volumes','full nuisance bounds','native-versus-restored protein amount','sampling distribution'],
 'reading_choice_ranges':{'meaning':'image of all256 joint +/-1pixel choices including shared axis positions; sensitivity only, not confidence or comprehensive error bound',
  'means_CFU_per_mL':{r:ranges(('means_CFU_per_mL',r)) for r in 'WKR'},
  'SD_CFU_per_mL':{r:ranges(('reported_SD_CFU_per_mL_graph_reading',r)) for r in 'WKR'},
  'components':{k:ranges(('components',k)) for k in point['components']}},
 'unchanged_source_bytes':hashlib.sha256(IMAGE.read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest(),
 'unavailable_components':{'reference_restoration_index':'no measured applicable C or nuisance-effect B bounds','index_confidence_interval':'no full joint sampling model; no invented independence','exact_paper_reported_WKR':'numeric means are graph-derived approximations here'},
 'limits':['paper caption supplies SD/n, graph supplies approximate magnitudes','axis/region nomination remains scientific reading work','SD is experimental spread; selected pixel range is separate reading-choice sensitivity','current finite production bar reader linear-axis scope is not claimed to implement this log-axis reading']}
with (BASE/'GRAPH_COMPONENTS_001.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'point':point,'reading_choice_components':report['reading_choice_ranges']['components'],'source_unchanged':report['unchanged_source_bytes']},indent=2))
