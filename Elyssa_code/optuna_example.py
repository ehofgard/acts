# Need to change python path before importing LIPO
import sys
sys.path.insert(0,'/afs/cern.ch/work/e/ehofgard/miniconda3/lib/python3.7/site-packages')

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
    maxPtScattering = trial.suggest_float("maxPtScattering",1200,500000)
    params.append(maxPtScattering)
    impactMax = trial.suggest_float("impactMax",0.1,25)
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
    cotThetaMax = trial.suggest_float("cotThetaMax",5.0,10.0)
    params.append(cotThetaMax)
    keys = ["maxPtScattering","impactMax","deltaRMin", "sigmaScattering", "deltaRMax", "maxSeedsPerSpM", "radLengthPerSeed","cotThetaMax"]
    for i in range(len(keys)):
        alg_stats[keys[i]].append(params[i])
    arg = paramsToInput(params,keys)
    r = executeAlg(arg)
    if len(r) != 0:
        dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
        alg_stats["eff"].append(eff)
        alg_stats["dup"].append(dup)
        alg_stats["fake"].append(fake)
        alg_stats["time"].append(r['time'])
    else:
        dup, eff, fake = np.nan, np.nan, np.nan, np.nan
    penalty = dup/(BIGK) + fake + r['time']/(BIGK)
    # if efficiency = 0, we want to make the penalty zero to maximize
    if eff == 0:
        penalty = 0
    print(eff-penalty,flush=True)
    print("Iteration Number: ",flush=True)
    print(len(alg_stats['eff']),flush=True)
    alg_stats["score"].append(eff-penalty)
    return eff - penalty

# Initial guess here
# Trying initial guess as original CKF parameters
optuna.logging.get_logger("optuna").addHandler(logging.StreamHandler(sys.stdout))
study_name = "itk_study_time_K7_150_generic_barrel"  # Unique identifier of the study.
storage_name = "sqlite:///{}.db".format(study_name)
#optuna.delete_study(study_name=study_name, storage=storage_name)
study = optuna.create_study(study_name=study_name, load_if_exists =True,direction='maximize')

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

study.optimize(objective, n_trials=150)
print("Best trial until now:",flush=True)
print(" Value: ", study.best_trial.value,flush=True)
print(" Params: ",flush=True)
for key, value in study.best_trial.params.items():
    print(f"    {key}: {value}",flush=True)

with open('optuna_time_K7_1GeV_150_generic_barrel/all_results_itk_test.json', 'w') as fp:
    json.dump(alg_stats,fp)

fig_hist = plot_optimization_history(study)
fig_hist.write_image("optuna_time_K7_1GeV_150_generic_barrel/opt_history.jpeg")
#fig_contour = plot_contour(study, params=["maxPtScattering","impactMax",
#"deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM","radLengthPerSeed"])
#fig_contour.write_image("optuna_plots_nostart_defaultconfig_K3_fake_moreparams/opt_contour.jpeg")
fig_parallel = plot_parallel_coordinate(study,params=["maxPtScattering","impactMax",
    "deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM","radLengthPerSeed","cotThetaMax"])
#"collisionReg","z","rMin","rMax"])
fig_parallel.write_image("optuna_time_K7_1GeV_150_generic_barrel/opt_parallel.jpeg")
fig_slice1 = plot_slice(study,params=["maxPtScattering","impactMax",
"deltaRMin","sigmaScattering","deltaRMax","maxSeedsPerSpM"])
fig_slice1.write_image("optuna_time_K7_1GeV_150_generic_barrel/opt_slice1.jpeg")
fig_slice2 = plot_slice(study, params = ["radLengthPerSeed","cotThetaMax"])
#"collisionReg","z","rMin","rMax"])
fig_slice2.write_image("optuna_time_K7_1GeV_150_generic_barrel/opt_slice2.jpeg")
fig_importance = plot_param_importances(study)
fig_importance.write_image("optuna_time_K7_1GeV_150_generic_barrel/opt_import.jpeg")
## Parameters that impact the trial duration
fig_importance_duration = plot_param_importances(
    study, target=lambda t: t.duration.total_seconds(), target_name="duration"
)
fig_importance_duration.write_image("optuna_time_K7_1GeV_150_generic_barrel/opt_import_duration.jpeg")
