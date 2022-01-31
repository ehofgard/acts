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
def function(maxSeedsPerSpM):
    saved_args = locals()
    zdict = {"a": 1, "b": 2}
    # would call the function here/open a subprocess
    return -((x - 1.23) ** 6) + -((y - 0.3) ** 4) * zdict[z]

# Initial guess here
pre_eval_x = dict(x=2.3, y=13, z="b")
evaluations = [(pre_eval_x, function(**pre_eval_x))]

search = GlobalOptimizer(
    function,
    lower_bounds={"x": -10.0, "y": -10},
    upper_bounds={"x": 10.0, "y": -3},
    categories={"z": ["a", "b"]},
    evaluations=evaluations,
    maximize=True,
)

# This may pose an issue w/ evaluating so many times
num_function_calls = 1000
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
           '--output-ML','True','--input-dir=/afs/cern.ch/work/e/ehofgard/acts/data/sim_generic/ttbar_mu200_1event',
           '--loglevel', '5','--sf-bFieldInZ', '1.99724','--sf-collisionRegionMin','-250','--sf-collisionRegionMax','250','--sf-zMin','-2000','--sf-zMax','2000'] 
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
