# Need to change python path before importing LIPO
import sys
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

BIGK = 7
alg_stats = {"eff":[],"dup":[],"fake": [],"score": [], "maxPtScattering":[],"impactMax": [], "deltaRMin": [], "sigmaScattering": [], "deltaRMax": [], "maxSeedsPerSpM": [],
"radLengthPerSeed": [], "cotThetaMax": []}
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
    ret = ['python3', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Scripts/Python/ckf_tracks_opt.py','--input_dir', '/afs/cern.ch/work/e/ehofgard/acts/data/gen/ttbar_mu200_1event_test/particles.root','--outputIsML']
    '''
    ret = ['/afs/cern.ch/work/e/ehofgard/acts/build/bin/ActsExampleCKFTracksGeneric',
           '--ckf-selection-chi2max', '15', '--bf-constant-tesla=0:0:2',
           '--ckf-selection-nmax', '10', 
           '--digi-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/Digitization/share/default-smearing-config-generic.json', 
           '--geo-selection-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/TrackFinding/share/geoSelection-genericDetector.json',
           '--output-ML','True','--input-dir=/afs/cern.ch/work/e/ehofgard/acts/data/sim_generic/ttbar_mu200_1event','--loglevel', '5']
    '''
    if len(params) != len(names):
        raise Exception("Length of Params must equal names in paramsToInput")
    i = 0
    for param in params:
        arg = "--sf_" + names[i]
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
    p3 = subprocess.Popen(
        ['grep', 'Average time per event'], stdin = subprocess.PIPE, stdout=subprocess.PIPE)
    output = p3.communicate(input = p1_out)[0].decode().strip()
    print(output)
    time = output.split(':')[-1]
    time = float(time.split(' ')[1])
    ret = {}

    if len(tokenizedOutput) != 1:
        ret['eff'] = float(tokenizedOutput[2])
        ret['fake'] = float(tokenizedOutput[4])
        ret['dup'] = float(tokenizedOutput[6])
        ret['time'] = float(time)
        return ret
    else:
        # Bad input parameters make the seeding algorithm break
        # kind of a bad solution but not sure what else to do here
        ret['eff'] = 0
        ret['dup'] = 1
        ret['fake'] = 1
        ret['time'] = 1
        return ret
    

def function(maxPtScattering, impactMax, deltaRMin, sigmaScattering, deltaRMax, maxSeedsPerSpM, radLengthPerSeed, cotThetaMax):
    saved_args = locals()
    for key in saved_args:
        alg_stats[key].append(saved_args[key])
    arg = paramsToInput(saved_args)
    r = executeAlg(arg)
    print(r)
    if len(r) != 0:
        dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
        alg_stats["eff"].append(eff)
        alg_stats["dup"].append(dup)
        alg_stats["fake"].append(fake)
    else:
        dup, eff, fake = np.nan, np.nan, np.nan
    penalty = dup/(BIGK) + fake + r['time']/(BIGK)
    if eff == 0:
        penalty = 0
    print(eff-penalty)
    print("Iteration Number: ")
    print(len(alg_stats['eff']))
    alg_stats["score"].append(eff-penalty)
    return eff - penalty

# Initial guess here
# Trying initial guess as original CKF parameters
#pre_eval_x = dict(maxPtScattering = 30000, impactMax = 1.1, deltaRMin = 0.25, sigmaScattering = 4.0, deltaRMax = 60.0, maxSeedsPerSpM = 1, radLengthPerSeed=0.0023)


search = GlobalOptimizer(
    function,
    lower_bounds = {"maxPtScattering": 1200, "impactMax": 0.1, "deltaRMin": 0.25, "sigmaScattering": 0.2, "deltaRMax": 50.0, "maxSeedsPerSpM": 0, "radLengthPerSeed": 0.001,"cotThetaMax": 5.0},
    upper_bounds = {"maxPtScattering": 500000, "impactMax": 20.0, "deltaRMin": 30.0, "sigmaScattering": 50.0, "deltaRMax": 300.0, "maxSeedsPerSpM": 10, "radLengthPerSeed": 0.1, "cotThetaMax": 10.0},
    #evaluations=evaluations,
    maximize=True,
)

num_function_calls = 150
search.run(num_function_calls)
optimal_val = search.optimum
print(optimal_val)
with open('all_results_lipo_time_150_generic_K7_barrel.json', 'w') as fp:
    json.dump(alg_stats,fp)
with open('best_result_time_150_generic_K7_barrel.json', 'w') as fp:
    json.dump(optimal_val,fp)
