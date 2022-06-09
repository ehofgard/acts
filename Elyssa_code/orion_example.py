# Need to change python path before importing LIPO
import sys
sys.path.insert(0,'/afs/cern.ch/work/e/ehofgard/miniconda3/lib/python3.7/site-packages')

import logging
from orion.client import build_experiment

import pathlib
import random
import subprocess
import multiprocessing
import numpy as np
import json
import array
import sys
count = 0

BIGK = 7
alg_stats = {"eff":[],"dup":[],"fake": [],"score": [], "maxPtScattering":[],"impactMax": [], "deltaRMin": [], "sigmaScattering": [], "deltaRMax": [], "maxSeedsPerSpM": [],
"radLengthPerSeed": [], "cotThetaMax" : [], "collisionRegionMin": [], 'collisionRegionMax': [],'zMin': [], 'zMax': [],'rMin' : [],'rMax' : []}
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
def paramsToInput(params,names):
    ret = ['python3', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Scripts/Python/ckf_tracks_opt.py','--input_dir', '/afs/cern.ch/work/e/ehofgard/acts/data/gen/ttbar_mu200_1event_test/particles.root','--outputIsML']
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
    p2 = subprocess.Popen(
        arg, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, universal_newlines=False)
    p2.stdin.flush()
    p2.stdout.flush()
    p1_out, p1_err = p2.communicate()
    p1_out = p1_out.decode()
    p1_out = p1_out.strip().encode()
    p2 = subprocess.Popen(
        ['grep', 'mlTag'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
    tokenizedOutput = output.split(',')
    p3 = subprocess.Popen(
        ['grep', 'Average time per event'], stdin = subprocess.PIPE, stdout=subprocess.PIPE)
    output = p3.communicate(input = p1_out)[0].decode().strip()
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
        ret['eff'] = 0
        ret['dup'] = 1
        ret['fake'] = 1
        ret['time'] = 1
        return ret
    
def score_func(maxPtScattering,impactMax,deltaRMin,sigmaScattering,deltaRMax,maxSeedsPerSpM,radLengthPerSeed,cotThetaMax):
    params = [maxPtScattering,impactMax,deltaRMin,sigmaScattering,deltaRMax,maxSeedsPerSpM,radLengthPerSeed,cotThetaMax]
    keys = ["maxPtScattering","impactMax","deltaRMin", "sigmaScattering", "deltaRMax", "maxSeedsPerSpM", "radLengthPerSeed","cotThetaMax"]
    arg = paramsToInput(params,keys)
    r = executeAlg(arg)
    if len(r) != 0:
        dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
    else:
        dup, eff, fake = np.nan, np.nan, np.nan
    penalty = dup/(BIGK) + fake + r['time']/(BIGK)
    # if efficiency = 0, we want to make the penalty zero to maximize
    if eff == 0:
        penalty = 0
    # Note Orion minimizes
    global count
    count += 1
    print(count)
    return [{"name": "objective", "type": "objective", "value": -(eff-penalty)}]


# Try visualization for parameter space
storage = {
    "type": "legacy",
    "database": {
        "type": "pickleddb",
        "host": "./db.pkl",
    },
}

space = {"maxPtScattering": "uniform(1200,500000)",
"impactMax": "uniform(0.1,20)",
"deltaRMin": "uniform(0.25, 30)",
"sigmaScattering": "uniform(0.2,50)",
"deltaRMax": "uniform(50,300)",
"maxSeedsPerSpM":"uniform(0,10,discrete=True)",
"radLengthPerSeed":"uniform(.001,0.1)",
"cotThetaMax": "uniform(5.0,10.0)"}

experiment = build_experiment(
    "orion_150_time_generic_K7_barrel",
    space=space,
    storage=storage,
)


experiment.workon(score_func, max_trials=150)
fig = experiment.plot.regret()
fig.write_image('test_regret.png')
fig = experiment.plot.parallel_coordinates()
fig.write_image('test_parallel_coord.png')
fig = experiment.plot.lpi()
fig.write_image('test_lpi.png')
fig = experiment.plot.partial_dependencies()
fig.write_image('test_dependency.png')

# To fetch trials in a form on panda dataframe
df = experiment.to_pandas()
df.to_csv("orion_150_time_generic_K7_barrel")
