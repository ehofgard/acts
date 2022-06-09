# Need to change python path before importing
import sys
sys.path.insert(0,'/afs/cern.ch/work/e/ehofgard/miniconda3/lib/python3.7/site-packages')

import logging
import skopt

import pathlib
import random
import subprocess
import multiprocessing
import numpy as np
import json
import array
import sys
import pandas as pd
count = 0

BIGK = 7
alg_stats = {"eff":[],"dup":[],"fake": [],"time": [],"score": [], "maxPtScattering":[],"impactMax": [], "deltaRMin": [], "sigmaScattering": [], "deltaRMax": [], "maxSeedsPerSpM": [],
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
    # Add timing here, or just add to mlTag info
    p2 = subprocess.Popen(
        ['grep', 'mlTag'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
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

space = [
    skopt.space.Real(1200,500000,name="maxPtScattering",prior="uniform"),
    skopt.space.Real(0.1,20,name="impactMax",prior="uniform"),
    skopt.space.Real(0.25,30,name="deltaRMin",prior="uniform"),
    skopt.space.Real(0.2,50,name="sigmaScattering",prior='uniform'),
    skopt.space.Real(50,300,name="deltaRMax",prior="uniform"),
    skopt.space.Integer(0,10,name="maxSeedsPerSpM"),
    skopt.space.Real(.001,.1,name="radLengthPerSeed",prior="uniform"),
    skopt.space.Real(5,10,name="cotThetaMax",prior="uniform")
]

@skopt.utils.use_named_args(space)
def objective(**params):
    params = locals()['params'].values()
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
    return -(eff-penalty)

# there are also different algorithms
results = skopt.forest_minimize(objective,space,n_calls=100)
print(results)
'''
plot_dir = "skopt_plots/"
skopt.plots.plot_convergence(results)
plt.savefig(plot_dir+"convergence.png")

skopt.plots.plot_objective(results)
plt.savefig(plot_dir+"objective.png")

skopt.plots.plot_regret(results)
plt.savefig(plot_dir+"regret.png")
'''

# This might not work
#skopt.dump(results, 'scikit_forest_results.pkl',store_objective=False)
# for now just save the results object to analyze later
# can look at visualizations https://neptune.ai/blog/scikit-optimize
