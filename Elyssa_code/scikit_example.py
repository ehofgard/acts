# Need to change python path before importing LIPO
import sys
# This is a strange way to fix it, but not sure how else to with weird CFG stuff
sys.path.insert(0,'/afs/cern.ch/work/e/ehofgard/miniconda3/lib/python3.7/site-packages')

#from lipo import GlobalOptimizer
#from collections import OrderedDict

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

# Put parameters as arguments here
# Need to keep the names of the arguments straight
BIGK = 3
#print(console.log(Object.keys(GlobalOptimizer)))
 
### NEED TO ADD SIGMA ERROR TO OPTIONS ###
alg_stats = {"eff":[],"dup":[],"fake": [],"score": [], "maxPtScattering":[],"impactMax": [], "deltaRMin": [], "sigmaScattering": [], "deltaRMax": [], "maxSeedsPerSpM": [],
"radLengthPerSeed": [], "cotThetaMax" : [], "collisionRegionMin": [], 'collisionRegionMax': [],'zMin': [], 'zMax': [],'rMin' : [],'rMax' : []}
# "sigmaError": []
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
    # just adding bFieldInZ as parameter here, doesn't really make sense to adjust
    #params = list(saved_args.values())
    #names = list(saved_args.keys())

    # figure out what is happening with bf constant tesla argument
    # need to regenerate data because this isn't working
    ret = ['python3', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Scripts/Python/ckf_tracks_opt.py','--input_dir', '/afs/cern.ch/work/e/ehofgard/acts/data/gen/ttbar_mu200_1event_test/particles.root','--outputIsML']
           #'--sf-rMax', '200',
           #'--sf-collisionRegionMin','-250','--sf-collisionRegionMax','250','--sf-zMin','-2000','--sf-zMax','2000',
           #'--sf-cotThetaMax','7.40627','--sf-minPt','500','--sf-bFieldInZ','1.99724']
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
        arg, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, universal_newlines=False)
    p2.stdin.flush()
    p2.stdout.flush()
    p1_out, p1_err = p2.communicate()
    #print(p1_out)
    p1_out = p1_out.decode()
    p1_out = p1_out.strip().encode()
    #print(p1_out)
    # Add timing here, or just add to mlTag info
    p2 = subprocess.Popen(
        ['grep', 'mlTag'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
    #print(output)
    tokenizedOutput = output.split(',')
    #print(tokenizedOutput)
    # this is a really dumb way to do this
    # otherwise would have to go into sequencer code
    '''
    p3 = subprocess.Popen(
        ['grep', 'Average time per event'], stdin = subprocess.PIPE, stdout=subprocess.PIPE)
    output = p3.communicate(input = p1_out)[0].decode().strip()
    print(output)
    time = output.split(':')[-1]
    time = float(time.split(' ')[1])
    '''
    ret = {}
    if len(tokenizedOutput) != 1:
        ret['eff'] = float(tokenizedOutput[2])
        ret['fake'] = float(tokenizedOutput[4])
        ret['dup'] = float(tokenizedOutput[6])
        return ret
    else:
        # Bad input parameters make the seeding algorithm break
        # kind of a bad solution but not sure what else to do here
        ret['eff'] = 0
        ret['dup'] = 1
        ret['fake'] = 1
        return ret
    '''
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
    '''

space = [
    skopt.space.Real(1200,1234567,name="maxPtScattering",prior="uniform"),
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
    #,"collisionRegionMin",
    #"collisionRegionMax","zMin","zMax","rMin","rMax"]
    # "sigmaError",
    #params = ["impactMax"]
    arg = paramsToInput(params,keys)
    #print(arg)
    r = executeAlg(arg)
    #print(r)
    if len(r) != 0:
        dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
    else:
        dup, eff, fake = np.nan, np.nan, np.nan
    # fake * dup / (BIGK)
    penalty = dup/(BIGK) - fake
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
skopt.dump(results, 'scikit_results.pkl',store_objective=False)

plot_dir = "skopt_plots/"
skopt.plots.plot_convergence(results)
plt.savefig(plot_dir+"convergence.png")

skopt.plots.plot_objective(results)
plt.savefig(plot_dir+"objective.png")

skopt.plots.plot_regret(results)
plt.savefig(plot_dir+"regret.png")

# for now just save the results object to analyze later
# can look at visualizations https://neptune.ai/blog/scikit-optimize
