# Need to change python path before importing LIPO
import sys
# This is a strange way to fix it, but not sure how else to with weird CFG stuff
sys.path.insert(0,'/afs/cern.ch/work/e/ehofgard/miniconda3/lib/python3.7/site-packages')

#from lipo import GlobalOptimizer
#from collections import OrderedDict

import logging
import argparse

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
from orion.client import report_objective

# Put parameters as arguments here
# Need to keep the names of the arguments straight
BIGK = 3
#print(console.log(Object.keys(GlobalOptimizer)))

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
    p1_out = p1_out.decode()
    p1_out = p1_out.strip().encode()
    #print(p1_out)
    # Add timing here, or just add to mlTag info
    p2 = subprocess.Popen(
        ['grep', 'mlTag'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2.stdin.flush()
    p2.stdout.flush()
    output = p2.communicate(input=p1_out)[0].decode().strip()
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
   

# get parameters here for Orion
# note this assumes they are passed in order
# just try maxPtScattering as a test
keys = ["maxPtScattering"]
#,"impactMax","deltaRMin", "sigmaScattering", "deltaRMax", "maxSeedsPerSpM", "radLengthPerSeed","cotThetaMax"]
args = []
for i in range(1,len(sys.argv)):
    args.append(sys.argv[i])
alg_input = paramsToInput(args,keys)
ret = executeAlg(alg_input)
if len(r) != 0:
    dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
    alg_stats["eff"].append(eff)
    alg_stats["dup"].append(dup)
    alg_stats["fake"].append(fake)
else:
    dup, eff, fake = np.nan, np.nan, np.nan
# fake * dup / (BIGK)
## Note orion wants minimization
penalty = -(dup/(BIGK) - fake)
# if efficiency = 0, we want to make the penalty zero to maximize
if eff == 0:
    penalty = 0
report_objective(penalty)
