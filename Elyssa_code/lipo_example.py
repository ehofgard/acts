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

# Put parameters as arguments here
# Need to keep the names of the arguments straight
BIGK = 3

def function(impactMax):
    saved_args = locals()
    params = ["impactMax"]
    arg = paramsToInput(params,saved_args)
    r = executeAlg(arg)
    if len(r) != 0:
        dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
    else:
        dup, eff, fake = np.nan, np.nan, np.nan
    # fake * dup / (BIGK)
    penalty = dup/(BIGK)
    #param_dist = dict(zip(params,saved_args))
    # zdict = {"a": 1, "b": 2}A
    # would call the function here/open a subprocess
    return eff - penalty

# Initial guess here
pre_eval_x = dict(impactMax = 0.5)
evaluations = [(pre_eval_x, function(**pre_eval_x))]

search = GlobalOptimizer(
    function,
    lower_bounds = {"impactMax": 0.1},
    upper_bounds = {"impactMax": 20},
    evaluations=evaluations,
    maximize=True,
)

# This may pose an issue w/ evaluating so many times
num_function_calls = 2
search.run(num_function_calls)

# Format the input for the seeding algorithm. 
# Assumes program is in same directory as seeding algorithm
def paramsToInput(params, names):
    # just adding bFieldInZ as parameter here, doesn't really make sense to adjust
    ret = ['/afs/cern.ch/work/e/ehofgard/acts/build/bin/ActsExampleCKFTracksGeneric',
           '--ckf-selection-chi2max', '15', '--bf-constant-tesla=0:0:2',
           '--ckf-selection-nmax', '10', 
           '--digi-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/Digitization/share/default-smearing-config-generic.json', 
           '--geo-selection-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/TrackFinding/share/geoSelection-genericDetector.json',
           '--output-ML','True','--input-dir=/afs/cern.ch/work/e/ehofgard/acts/data/sim_generic/muon_data_10events',
           '--loglevel', '5']
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
    p2 = subprocess.Popen(
        arg, bufsize=4096, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p1_out, p1_err = p2.communicate()
    p1_out = p1_out.decode()
    p1_out = p1_out.strip().encode()
    p2 = subprocess.Popen(
        ['grep', mlTag], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
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
        return ret
    if ret['eff'] == 0:
        print("0 efficiency error: ")
        print(arg)
        print(p1_out)
        print(p1_err)
