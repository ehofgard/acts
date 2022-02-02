# Need to change python path before importing LIPO
import sys
# This is a strange way to fix it, but not sure how else to with weird CFG stuff
sys.path.insert(0,'/afs/cern.ch/user/e/ehofgard/.local/lib/python3.7/site-packages')

from lipo import GlobalOptimizer
from collections import OrderedDict

import pathlib
import matplotlib
matplotlib.use('pdf')
import matplotlib.pyplot as plt
import random
import subprocess
import multiprocessing
import numpy as np
import json
import array
import sys

# Put parameters as arguments here
# Need to keep the names of the arguments straight
BIGK = 3
#print(console.log(Object.keys(GlobalOptimizer)))
alg_stats = {"eff":[],"dup":[],"fake": [],"maxPtScattering":[],"impactMax": [], "deltaRMin": [], "sigmaScattering": [], "deltaRMax": [], "maxSeedsPerSpM": [],
"radLengthPerSeed": []}
effs = []
dups = []
fakes = []
scores = []
maxPtScatterings = []
impactMaxs = []
deltaRMins = []
sigmaScatterings = []
deltaRMaxs = []
maxSeedsPerSpMs = []
radLengthPerSeeds = []

# Format the input for the seeding algorithm. 
# Assumes program is in same directory as seeding algorithm
def paramsToInput(saved_args):
    # just adding bFieldInZ as parameter here, doesn't really make sense to adjust
    params = list(saved_args.values())
    names = list(saved_args.keys())
    ret = ['/afs/cern.ch/work/e/ehofgard/acts/build/bin/ActsExampleCKFTracksGeneric',
           '--ckf-selection-chi2max', '15', '--bf-constant-tesla=0:0:2',
           '--ckf-selection-nmax', '10', 
           '--digi-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/Digitization/share/default-smearing-config-generic.json', 
           '--geo-selection-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/TrackFinding/share/geoSelection-genericDetector.json',
           '--output-ML','True','--input-dir=/afs/cern.ch/work/e/ehofgard/acts/data/sim_generic/ttbar_mu200_1event','--loglevel', '5']
    if len(params) != len(names):
        raise Exception("Length of Params must equal names in paramsToInput")
    i = 0
    for param in params:
        arg = "--sf-" + names[i]
        ret.append(arg)
        paramValue = param
        ret.append(str(paramValue))
        i += 1
    return ret

# Opens a subprocess that runs the seeding algorithm and retrieves output using grep
# Returns efficiency, fake rate, and duplicate rate as percentages
def executeAlg(arg):
    #sys.path.remove('/afs/cern.ch/user/e/ehofgard/.local/lib/python3.7/site-packages')
    p2 = subprocess.Popen(
        arg, bufsize=4096, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p1_out, p1_err = p2.communicate()
    p1_out = p1_out.decode()
    p1_out = p1_out.strip().encode()
    p2 = subprocess.Popen(
        ['grep', 'mlTag'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    output = p2.communicate(input=p1_out)[0].decode().strip()
    tokenizedOutput = output.split(',')
    ret = {}
    if len(tokenizedOutput) != 1:
        ret['eff'] = float(tokenizedOutput[2])
        ret['fake'] = float(tokenizedOutput[4])
        ret['dup'] = float(tokenizedOutput[6])
    if len(tokenizedOutput) == 1:
        print("Timeout error ")
        print(arg)
        print(p1_out)
        print(p1_err)
    if ret['eff'] == 0:
        print("0 efficiency error: ")
        print(arg)
        print(p1_out)
        print(p1_err)
    return ret
    

def function(maxPtScattering, impactMax, deltaRMin, sigmaScattering, deltaRMax, maxSeedsPerSpM, radLengthPerSeed):
    saved_args = locals()
    #params = ["impactMax"]
    for key in saved_args:
        alg_stats[key].append(saved_args[key])
    arg = paramsToInput(saved_args)
    r = executeAlg(arg)
    #print(r)
    if len(r) != 0:
        dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
        alg_stats["eff"].append(eff)
        alg_stats["dup"].append(dup)
        alg_stats["fake"].append(fake)
    else:
        dup, eff, fake = np.nan, np.nan, np.nan
    # fake * dup / (BIGK)
    penalty = dup/(BIGK)
    #param_dist = dict(zip(params,saved_args))
    # zdict = {"a": 1, "b": 2}A
    # would call the function here/open a subprocess
    scores.append(eff-penalty)
    return eff - penalty

# Initial guess here
pre_eval_x = dict(maxPtScattering = 30000, impactMax = 1.1, deltaRMin = 0.25, sigmaScattering = 4.0, deltaRMax = 60.0, maxSeedsPerSpM = 1, radLengthPerSeed=0.0023)
evaluations = [(pre_eval_x, function(**pre_eval_x))]

search = GlobalOptimizer(
    function,
    lower_bounds = {"maxPtScattering": 1200, "impactMax": 0.1, "deltaRMin": 0.25, "sigmaScattering": 0.2, "deltaRMax": 50.0, "maxSeedsPerSpM": 0, "radLengthPerSeed": 0.001},
    upper_bounds = {"maxPtScattering": 1234567, "impactMax": 20.0, "deltaRMin": 30.0, "sigmaScattering": 50.0, "deltaRMax": 300.0, "maxSeedsPerSpM": 10, "radLengthPerSeed": 0.025},
    evaluations=evaluations,
    maximize=True,
)

# This may pose an issue w/ evaluating so many times
num_function_calls = 1000
search.run(num_function_calls)
#print(search.evaluations)
optimal_val = search.optimum
print(optimal_val)
print(alg_stats)
with open('all_results_lipo.json', 'w') as fp:
    json.dump(alg_stats,fp)
with open('best_result.json', 'w') as fp:
    json.dump(optimal_val,fp)
