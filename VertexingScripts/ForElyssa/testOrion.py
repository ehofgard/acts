#!/usr/bin/env python3
import sys
#importing packages directly from conda environment (acts environment conflicts with conda upon activating)
sys.path.insert(0,'/afs/cern.ch/work/r/rgarg/public/miniconda3/envs/myEnv_ParOpti/lib/python3.7/site-packages')

import logging
from orion.client import build_experiment
#from orion.client import create_experiment

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
count = 0

#from Execution import paramsToInput, executeAlg

## keeping a log of parameter values
alg_stats = {"score": [], "eff_total": [], "eff_clean": [], "merge": [], "split": [], "fake": [], "res": [], "tracksMaxZinterval": [], "tracksMaxSignificance": [], "maxVertexChi2": [], "maxMergeVertexSignificance": [], "minWeight": [], "maxIterations": [], "maximumVertexContamination": []}

def paramsToInput(params,names):
    
    if len(params) != len(names):
        raise Exception("Length of Params must equal names in paramsToInput")

    ret = ['./runVertexing.sh']

    i = 0
    for param in params:
        arg = "--" + names[i] + "=" + str(param)
        ret.append(arg)
        i+=1

    return ret

def executeAlg(arg):

    p2 = subprocess.Popen(
        arg, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, universal_newlines=False)
    p2.stdin.flush()
    p2.stdout.flush()
    p1_out, p1_err = p2.communicate()
    p1_out = p1_out.decode()
    p1_out = p1_out.strip().encode()

    print(p1_out)

    ret = {}

    p2 = subprocess.Popen(
        ['grep', 'Efficiency of total reco vertices in event'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
    print("Output")
    print(output)
    tokenizedOutput = output.split(':')
    print(tokenizedOutput)
    if len(tokenizedOutput) != 1:
        ret['eff_total'] = float(tokenizedOutput[-1])
    else:
        ret['eff_total'] = 0

    p2 = subprocess.Popen(
        ['grep', 'Efficiency of clean reco vertices in event'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
    tokenizedOutput = output.split(':')
    print(tokenizedOutput)
    if len(tokenizedOutput) != 1:
        ret['eff_clean'] = float(tokenizedOutput[-1])
    else:
        ret['eff_clean'] = 0

    p2 = subprocess.Popen(
        ['grep', 'Fraction of merge reco vertices in event'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
    tokenizedOutput = output.split(':')
    print(tokenizedOutput)
    if len(tokenizedOutput) != 1:
        ret['merge'] = float(tokenizedOutput[-1])
    else:
        ret['merge'] = 1

    p2 = subprocess.Popen(
        ['grep', 'Fraction of split reco vertices in event'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
    tokenizedOutput = output.split(':')
    print(tokenizedOutput)
    if len(tokenizedOutput) != 1:
        ret['split'] = float(tokenizedOutput[-1])
    else:
        ret['split'] = 1

    p2 = subprocess.Popen(
        ['grep', 'Fraction of fake reco vertices in event'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
    tokenizedOutput = output.split(':')
    print(tokenizedOutput)
    if len(tokenizedOutput) != 1:
        ret['fake'] = float(tokenizedOutput[-1])
    else:
        ret['fake'] = 1

    p2 = subprocess.Popen(
        ['grep', 'Relative difference between true and reco vertex position'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
    tokenizedOutput = output.split(':')
    print(tokenizedOutput)
    if len(tokenizedOutput) != 1:
        ret['res'] = float(tokenizedOutput[-1])
    else:
        ret['res'] = 1

    return ret


def score_func(tracksMaxZinterval, tracksMaxSignificance, maxVertexChi2, maxMergeVertexSignificance, minWeight, maxIterations, maximumVertexContamination):
    
    params = [tracksMaxZinterval, tracksMaxSignificance, maxVertexChi2, maxMergeVertexSignificance, minWeight, maxIterations, maximumVertexContamination]
    keys = ["tracksMaxZinterval", "tracksMaxSignificance", "maxVertexChi2", "maxMergeVertexSignificance", "minWeight", "maxIterations", "maximumVertexContamination"]

    print("params")
    print(params)
    print("names")
    print(keys)
    arg = paramsToInput(params,keys)
    print(arg)
    r = executeAlg(arg)
    print(r)

    if len(r) != 0:
        eff_total, eff_clean, merge, split, fake, res = float(r['eff_total'])*100, float(r['eff_clean'])*100, float(r['merge'])*100, float(r['split'])*100, float(r['fake'])*100, float(r['res'])*100 
        #alg_stats["eff_total"].append(eff_total)
        #alg_stats["eff_clean"].append(eff_clean)
        #alg_stats["merge"].append(merge)
        #alg_stats["split"].append(split)
        #alg_stats["fake"].append(fake)
        #alg_stats["res"].append(res)
    else:
        eff_total, eff_clean, merge, split, fake, res = np.nan, np.nan, np.nan, np.nan, np.nan, 0.0

    eff = eff_total + 2 * eff_clean
    penalty = merge + split + fake + res

    if eff == 0:
        penalty = 0

    # Note Orion minimizes
    global count
    count += 1
    print("Iteration Number = %s"%(count))
    return [{"name": "objective", "type": "objective", "value": -(eff-penalty)}]
    #return -(eff - penalty)

def main():

    space = {"tracksMaxZinterval": "uniform(0.1, 6.0)", "tracksMaxSignificance": "uniform(1.0, 6.0)", "maxVertexChi2": "uniform(1.0, 30.0)", "maxMergeVertexSignificance": "uniform(0.1, 6.0)", "minWeight": "uniform(0.00001, 0.1)", "maxIterations": "uniform(10, 300)", "maximumVertexContamination": "uniform(0.1, 1.0)"}
    #space = dict(tracksMaxZinterval= "uniform(0.1, 6.0)", tracksMaxSignificance= "uniform(1.0, 6.0)", maxVertexChi2= "uniform(1.0, 30.0)", maxMergeVertexSignificance= "uniform(0.1, 6.0)", minWeight= "uniform(0.00001, 0.1)", maxIterations= "uniform(10, 300)", maximumVertexContamination= "uniform(0.1, 1.0)")

    
    # Try visualization for parameter space
    storage = {
        "type": "legacy",
        "database": {
            "type": "ephemeraldb"
            #"host": "./db.pkl",
        },
    }
    
    '''
    experiment = create_experiment(
        name = "orion_test",
        space=space
        )
    '''
    experiment = build_experiment(
        "orion_test",
        space=space,
        storage=storage
        #max_trials=10
    )

    '''
    while not experiment.is_done:
        trial = experiment.suggest()
        print("trial")
        print(trial)
        y = score_func(trial.params["tracksMaxZinterval", "tracksMaxSignificance", "maxVertexChi2", "maxMergeVertexSignificance", "minWeight", "maxIterations", "maximumVertexContamination"])
        print("y")
        print(y)
        
        experiment.observe(
            trial,
            [dict(
                name = "objective",
                type = 'objective',
                value = y)])
    '''



    experiment.workon(score_func, max_trials=10, n_workers=1)

    fig = experiment.plot.regret()
    fig.write_image('OptResults/Orion/test_regret.png')
    fig = experiment.plot.parallel_coordinates()
    fig.write_image('OptResults/Orion/test_parallel_coord.png')
    fig = experiment.plot.lpi()
    fig.write_image('OptResults/Orion/test_lpi.png')
    fig = experiment.plot.partial_dependencies()
    fig.write_image('OptResults/Orion/test_dependency.png')
    
    # To fetch trials in a form on panda dataframe
    df = experiment.to_pandas()
    df.to_csv("OptResults/Orion/orion_test")

    '''
    report_results([dict(
        name = 'Score',
        type = 'objective',
        value = score_func
    )])
    '''



if __name__ == "__main__":
    main()
