# Need to change python path before importing LIPO
import sys
# This is a strange way to fix it, but not sure how else to with weird CFG stuff
sys.path.insert(0,'/afs/cern.ch/work/e/ehofgard/miniconda3/lib/python3.7/site-packages')

#from lipo import GlobalOptimizer
#from collections import OrderedDict

import logging
import optuna

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
from optuna.visualization import plot_contour
from optuna.visualization import plot_edf
from optuna.visualization import plot_intermediate_values
from optuna.visualization import plot_optimization_history
from optuna.visualization import plot_parallel_coordinate
from optuna.visualization import plot_param_importances
from optuna.visualization import plot_slice

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
    ret = ['/afs/cern.ch/work/e/ehofgard/acts/build/bin/ActsExampleCKFTracksGeneric',
           '--ckf-selection-chi2max', '15', '--bf-constant-tesla=0:0:2',
           '--ckf-selection-nmax', '10', 
           '--digi-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/Digitization/share/default-smearing-config-generic.json', 
           '--geo-selection-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/TrackFinding/share/geoSelection-genericDetector.json',
           '--output-ML','True','--input-dir=/afs/cern.ch/work/e/ehofgard/acts/data/sim_generic/ttbar_mu200_1event','--loglevel', '5','--sf-minPt','500','--sf-bFieldInZ','1.99724']
           #'--sf-rMax', '200',
           #'--sf-collisionRegionMin','-250','--sf-collisionRegionMax','250','--sf-zMin','-2000','--sf-zMax','2000',
           #'--sf-cotThetaMax','7.40627','--sf-minPt','500','--sf-bFieldInZ','1.99724']
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
    

def objective(trial):
    params = []
    maxPtScattering = trial.suggest_float("maxPtScattering",1200,1234567)
    params.append(maxPtScattering)
    impactMax = trial.suggest_float("impactMax",0.1,20)
    params.append(impactMax)
    deltaRMin = trial.suggest_float("deltaRMin", 0.25, 30)
    params.append(deltaRMin)
    sigmaScattering = trial.suggest_float("sigmaScattering",0.2,50)
    params.append(sigmaScattering)
    deltaRMax = trial.suggest_float("deltaRMax",50,300)
    params.append(deltaRMax)
    maxSeedsPerSpM = trial.suggest_int("maxSeedsPerSpM",0,10)
    params.append(maxSeedsPerSpM)
    radLengthPerSeed = trial.suggest_float("radLengthPerSeed",.001,0.1)
    params.append(radLengthPerSeed)
    cotThetaMax = trial.suggest_float("cotThetaMax",5.0,15.0)
    params.append(cotThetaMax)
    #sigmaError = trial.suggest_float("sigmaError",2.0,10.0)
    #params.append(sigmaError)
    collisionReg = trial.suggest_float("collisionReg",100,350)
    params.append(-1*collisionReg)
    params.append(collisionReg)
    z = trial.suggest_float("z",1500,3000)
    params.append(-1*z)
    params.append(z)
    rMin = trial.suggest_float("rMin",20,50)
    params.append(rMin)
    rMax = trial.suggest_float("rMax",150,600)
    params.append(rMax)
    keys = ["maxPtScattering","impactMax","deltaRMin", "sigmaScattering", "deltaRMax", "maxSeedsPerSpM", "radLengthPerSeed","cotThetaMax","collisionRegionMin",
    "collisionRegionMax","zMin","zMax","rMin","rMax"]
    # "sigmaError",
    #params = ["impactMax"]
    for i in range(len(keys)):
        alg_stats[keys[i]].append(params[i])
    arg = paramsToInput(params,keys)
    #print(arg)
    r = executeAlg(arg)
    print(r)
    if len(r) != 0:
        dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
        alg_stats["eff"].append(eff)
        alg_stats["dup"].append(dup)
        alg_stats["fake"].append(fake)
    else:
        dup, eff, fake = np.nan, np.nan, np.nan
    # fake * dup / (BIGK)
    penalty = dup/(BIGK) - fake
    #param_dist = dict(zip(params,saved_args))
    # zdict = {"a": 1, "b": 2}A
    # would call the function here/open a subprocess
    print(eff-penalty)
    print("Iteration Number: ")
    print(len(alg_stats['eff']))
    alg_stats["score"].append(eff-penalty)
    return eff - penalty

# Initial guess here
# Trying initial guess as original CKF parameters
#pre_eval_x = dict(maxPtScattering = 30000, impactMax = 1.1, deltaRMin = 0.25, sigmaScattering = 4.0, deltaRMax = 60.0, maxSeedsPerSpM = 1, radLengthPerSeed=0.0023)
#optuna.delete_study(study_name="CKF-study-nostart_defaultconfig_K3_fake_moreparams",storage="sqlite:///{}.db".format("CKF-study-nostart_defaultconfig_K3_fake_moreparams"))
optuna.logging.get_logger("optuna").addHandler(logging.StreamHandler(sys.stdout))
study_name = "CKF-study-nostart_defaultconfig_K3_fake_moreparams"  # Unique identifier of the study.
storage_name = "sqlite:///{}.db".format(study_name)
study = optuna.create_study(study_name=study_name, storage=storage_name, load_if_exists = True,direction='maximize')

# Add initial parameters
# Also enqueue previously found parameters
'''
study.enqueue_trial(
    {
        "maxPtScattering": 30000,
        "impactMax": 1.1,
        "deltaRMin": 0.25,
        "sigmaScattering": 4.0,
        "deltaRMax": 60.0,
        "maxSeedsPerSpM": 1,
        "radLengthPerSeed": 0.0023
    }
)
'''


# Try visualization for parameter space

#study.optimize(objective, n_trials=1)
print("Best trial until now:")
print(" Value: ", study.best_trial.value)
print(" Params: ")
for key, value in study.best_trial.params.items():
    print(f"    {key}: {value}")
fig_hist = plot_optimization_history(study)
fig_hist.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_history.jpeg")
#fig_contour = plot_contour(study, params=["maxPtScattering","impactMax",
#"deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM","radLengthPerSeed"])
#fig_contour.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_contour.jpeg")
fig_parallel = plot_parallel_coordinate(study,params=["maxPtScattering","impactMax",
"deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM","radLengthPerSeed","cotThetaMax",
"collisionReg","z","rMin","rMax"])
fig_parallel.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_parallel.jpeg")
fig_slice1 = plot_slice(study,params=["maxPtScattering","impactMax",
"deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM"])
fig_slice1.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_slice1.jpeg")
fig_slice2 = plot_slice(study, params = ["radLengthPerSeed","cotThetaMax",
"collisionReg","z","rMin","rMax"])
fig_slice2.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_slice2.jpeg")
fig_importance = plot_param_importances(study)
fig_importance.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_import.jpeg")
## Parameters that impact the trial duration
fig_importance_duration = plot_param_importances(
    study, target=lambda t: t.duration.total_seconds(), target_name="duration"
)
fig_importance_duration.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_import_duration.jpeg")



