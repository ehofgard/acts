# Need to change python path before importing LIPO
import sys
# This is a strange way to fix it, but not sure how else to with weird CFG stuff
sys.path.insert(0,'/afs/cern.ch/work/e/ehofgard/miniconda3/lib/python3.7/site-packages')

#from lipo import GlobalOptimizer
#from collections import OrderedDict

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
    
def score_func(maxPtScattering,impactMax,deltaRMin,sigmaScattering,deltaRMax,maxSeedsPerSpM,radLengthPerSeed,cotThetaMax):
    params = [maxPtScattering,impactMax,deltaRMin,sigmaScattering,deltaRMax,maxSeedsPerSpM,radLengthPerSeed,cotThetaMax]
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
    return [{"name": "objective", "type": "objective", "value": -(eff-penalty)}]


# Try visualization for parameter space
storage = {
    "type": "legacy",
    "database": {
        "type": "pickleddb",
        "host": "./db.pkl",
    },
}

space = {"maxPtScattering": "uniform(1200,1234567)",
"impactMax": "uniform(0.1,20)",
"deltaRMin": "uniform(0.25, 30)",
"sigmaScattering": "uniform(0.2,50)",
"deltaRMax": "uniform(50,300)",
"maxSeedsPerSpM":"uniform(0,10,discrete=True)",
"radLengthPerSeed":"uniform(.001,0.1)",
"cotThetaMax": "uniform(5.0,10.0)"}

experiment = build_experiment(
    "orion_150_new",
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
df.to_csv("orion_150")

#with open('orion_testplots.json', 'w') as fp:
#    json.dump(alg_stats,fp)
'''
study.optimize(objective, n_trials=100)
#,n_jobs=-1)
print("Best trial until now:",flush=True)
print(" Value: ", study.best_trial.value,flush=True)
print(" Params: ",flush=True)
for key, value in study.best_trial.params.items():
    print(f"    {key}: {value}",flush=True)

with open('optuna_itk_test/all_results_itk_test.json', 'w') as fp:
    json.dump(alg_stats,fp)

fig_hist = plot_optimization_history(study)
fig_hist.write_image("optuna_itk_test/opt_history.jpeg")
#fig_contour = plot_contour(study, params=["maxPtScattering","impactMax",
#"deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM","radLengthPerSeed"])
#fig_contour.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_contour.jpeg")
fig_parallel = plot_parallel_coordinate(study,params=["maxPtScattering","impactMax",
    "deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM","radLengthPerSeed","cotThetaMax"])
#"collisionReg","z","rMin","rMax"])
fig_parallel.write_image("optuna_itk_test/opt_parallel.jpeg")
fig_slice1 = plot_slice(study,params=["maxPtScattering","impactMax",
"deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM"])
fig_slice1.write_image("optuna_itk_test/opt_slice1.jpeg")
fig_slice2 = plot_slice(study, params = ["radLengthPerSeed","cotThetaMax"])
#"collisionReg","z","rMin","rMax"])
fig_slice2.write_image("optuna_itk_test/opt_slice2.jpeg")
fig_importance = plot_param_importances(study)
fig_importance.write_image("optuna_itk_test/opt_import.jpeg")
## Parameters that impact the trial duration
fig_importance_duration = plot_param_importances(
    study, target=lambda t: t.duration.total_seconds(), target_name="duration"
)
fig_importance_duration.write_image("optuna_itk_test/opt_import_duration.jpeg")
'''



