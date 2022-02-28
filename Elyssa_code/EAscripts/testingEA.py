#!/usr/bin/env python3
from deap import cma
from deap import algorithms
from deap import tools
from deap import creator
from deap import base

import os
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
import pickle

# Command line arguments
# Implement this later

'''
 def getArgumentParser():
     Get arguments from the command line
     parser = argparse.ArgumentParser(description="Script to run evolutionary algorithm")
     parser.add_argument('-i',
                        '--infile',
                        dest = 'infile',
                        help = 'input ROOT file')
    parser.add_argument('-o',
                        '--outdir',
                        dest='outdir',
                        help = 'output directory for plots etc.',
                        default = 'outdir')
'''
    



# Definitions
# Tags to use for reading output from seeding algorithm
mlTag = 'mlTag'
effTag, dupTag, fakeTag = 'eff', 'dup', 'fake'
# used to be 50
NPOP = 50 # Population size
# INT_MIN, INT_MAX = 0, 5
# FLT_MIN, FLT_MAX = 0.2, 3.0
# Define bounds on parameters during training
# Need to change these bounds for optimization
#MINS = [0.1, 0.1, 0.05, 0.1, 0.8, 1.0, 0.1]
#MAXS = [999, 20, 8, 10, 2, 10, 10]
# doing a broader search here maybe?
# MINS = [0.1, 0.1, 0.1, 0.1, 0.1, 1, 0.1]
#MAXS = [100,100,100,100,100,100,100]
# Change these to follow process in testingES.py because they are currently breaking
# seeding algorithm
# Define bounds on parameters during training from testingES.py
#MINS = [1200, 0.1, 0.25, 0.2, 50, 0, 0.001] #, 0.001, 400, 5]
#MAXS = [1234567, 20, 30, 10, 200, 4, 0.02] #, 0.003, 600, 10]

# Dictionary of normalization coefficients
# because update for each parameter is drawn from the same normal distribution
# took out collision region
# setting these to be optimal parameters
NAME_TO_FACTOR = {'maxPt': 30000, 'impactMax': 1.1,
                  'deltaRMin': .25, 'sigmaScattering': 4, 'deltaRMax': 60.0, 'maxSeedsPerSpM': 1,'radLengthPerSeed': 0.0023}

# does maxSeedsPerSpM = 0 make sense?
#NAME_TO_FACTOR = {'maxPt': 50000, 'impactMax': 1.1,
#                  'deltaRMin': .25, 'sigmaScattering': 10, 'deltaRMax': 60.0, 'maxSeedsPerSpM': 1,'radLengthPerSeed': 0.0023}
NAME_TO_INDEX = {}
for i, key in enumerate(NAME_TO_FACTOR):
    NAME_TO_INDEX[key] = i
TournamentSize = 3 # Parameter used for selection
# used to be 200
NGEN = 16 # Number of generations
# SIGMA used to be 0.1
CXPB, MUTPB, SIGMA, INDPB = 0.5, 0.3, 1, 0.2
NAMES_DEF = []
for oneName in NAME_TO_FACTOR:
    NAMES_DEF.append(oneName)
# MIN_STRATEGY = 0.01
# MAX_STRATEGY = .5
# make these user arguments
plotDirectory = "EAmuongen_20events" # Where to save the plots
ttbarSampleInput = ['--input-dir', '/afs/cern.ch/work/e/ehofgard/acts/data/sim_generic/muon_data_10events']
ttbarSampleBool = True
bad_params = []

def normalizedToActual(normalizedInd):
    newDict = {}
    for i, name in enumerate(NAMES_DEF):
        if (name == 'maxSeedsPerSpM'):
            newDict[name] = int(NAME_TO_FACTOR[name] * normalizedInd[i])
        else:
            newDict[name] = NAME_TO_FACTOR[name] * normalizedInd[i]
    return newDict

# Create the names with the parameters for the seeding algo
def createNamesAndParams(individual):
    names = []
    params = []
    for i, name in enumerate(NAMES_DEF):
        names.append(name)
        if (name == 'maxSeedsPerSpM'):
            params.append(int(individual[i] * NAME_TO_FACTOR[name]))
        else:
            params.append(individual[i] * NAME_TO_FACTOR[name])
    return names, params

# Print an individual
def indPrint(ind):
    newInd = normalizedToActual(ind)
    commandLineInd = ''
    for argName in newInd:
        commandLineInd += ("--sf-" + argName + " " +
                           str(newInd[argName]) + " ")
    print(commandLineInd)

# Format the input for the seeding algorithm. 
# Assumes program is in same directory as seeding algorithm
# Adding the CKF parameters here
# Note, should probably change the code here
def paramsToInput(params, names):
    ret = ['/afs/cern.ch/work/e/ehofgard/acts/build/bin/ActsExampleCKFTracksGeneric',
           '--ckf-selection-chi2max', '15', '--bf-constant-tesla=0:0:2',
           '--ckf-selection-nmax', '10', 
           '--digi-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/Digitization/share/default-smearing-config-generic.json', 
           '--geo-selection-config-file', '/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/TrackFinding/share/geoSelection-genericDetector.json',
           '--output-ML','True','--input-dir=/afs/cern.ch/work/e/ehofgard/acts/data/sim_generic/muon_data_20events',
           '--loglevel', '4']
    '''
    if (ttbarSampleBool):
        ret.append(ttbarSampleInput[0])
        ret.append(ttbarSampleInput[1])
    '''
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

# Opens a subprocess that runs the CKF and retrieves output using grep
def executeAlg(arg):
    #print(arg)
    p2 = subprocess.Popen(
        arg, bufsize=4096, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p1_out, p1_err = p2.communicate()
    p1_out = p1_out.decode()
    #print(p1_out)
    #print(p1_err)
    p1_out = p1_out.strip().encode()
    p2 = subprocess.Popen(
        ['grep', mlTag], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    output = p2.communicate(input=p1_out)[0].decode().strip()
    #print(output)
    tokenizedOutput = output.split(',')
    #print(tokenizedOutput)
    ret = {}
    # Check for if the CKF actually ran or not
    #print(len(tokenizedOutput))
    if len(tokenizedOutput) != 1:
        ret['eff'] = float(tokenizedOutput[2])
        ret['fake'] = float(tokenizedOutput[4])
        ret['dup'] = float(tokenizedOutput[6])
    if ret['eff'] == 0:
        print("O efficieny error: ")
        print(arg)
        print(p1_out)
        print(p1_err)
    if len(tokenizedOutput) == 1:
        print("Bad input: ")
        print(arg)
        print(p1_out)
        print(p1_err)
        #print(p1_out)
    # should do this better
    '''
    print(tokenizedOutput)
    ret = {'dup': -1, 'eff': -1, 'fake':-1}
    for word in tokenizedOutput:
        if (word.find(dupTag) != -1):
            print(ret['dup'])
            ret['dup'] = word[len(dupTag):]
        if (word.find(effTag) != -1):
            ret['eff'] = (word[len(effTag):])
        if (word.find(fakeTag) != -1):
            ret['fake'] = (word[len(fakeTag):])
        #if (word.find(truthTag) != -1):
        #    ret['tSeeds'] = (word[len(truthTag):])
    '''
    return ret

# weights used to be (1.0,-1.0,-1.0)
# was playing around with this, need to use score function here
creator.create("Fitness", base.Fitness, weights=(1.0, -1.0, -1.0))
#creator.create("Fitness", base.Fitness, weights=(2.0, -1.0, -5.0))
creator.create("Individual", array.array, typecode="d",
               fitness=creator.Fitness, strategy=None)
# creator.create("Strategy", array.array, typecode="d")


# Initializes a population from a single individual
def initPopulation(pcls, ind_init, filename):
    with open(filename, "r") as pop_file:
        contents = json.load(pop_file)
    #print(contents)
    pop = pcls(ind_init(contents) for i in range(NPOP))
    # for ind in pop:
    #     ind.strategy = scls(random.uniform(smin, smax) for _ in range(size))
    return pop


toolbox = base.Toolbox()

# toolbox.register("attr_int", random.randint, INT_MIN, INT_MAX)
# toolbox.register("attr_flt", random.uniform, FLT_MIN, FLT_MAX)
# toolbox.register("individual", tools.initRepeat, creator.Individual,
#                  toolbox.attr_flt, n=N_CYCLES)
toolbox.register("population_guess", initPopulation, list,
                 creator.Individual, "my_guess.json")

# Evaluates an individual and calculates a score
def evaluate(individual):
    names, params = createNamesAndParams(individual)
    #print("params")
    #print(dict(zip(names,params)))
    arg = paramsToInput(params, names)
    r = executeAlg(arg)
    if len(r) != 0:
        dup, eff, fake = 100*float(r['dup']), 100*float(r['eff']), 100*float(r['fake'])
    else:
        # need to fix this but initializing to dummy parameters if CKF config breaks
        # set better bounds on parameters to avoid doing this probably
        # in theory these would be the worst parameters
        # need to fix this
        # something like if CKF returns empty just skip that individual
        #dup, eff, fake = -100,-100,-100
        #dup, eff, fake = 100,0,100
        dup, eff, fake = np.nan, np.nan, np.nan
        # MAX_SEEDS = 20000
        # seedsScore = 10 * float(seeds) / MAX_SEEDS
        bad_params.append(dict(zip(names,params)))
    '''
    nSeeds, nTrueSeeds, nDup = float(seeds), float(trueSeeds), float(dup)
    fakeRate = 100 * (nSeeds - nTrueSeeds) / nSeeds
    duplicateRate = 100 * nDup / nTrueSeeds
    effScore = (1 / (1 - (float(eff) / 100)))
    '''
    return eff, fake, dup

# Forces individual to stay within bounds after an update
# Change this to be within bounds that converge
def checkBounds(mins, maxs):
    def decorator(func):
        def wrapper(*args, **kargs):
            offspring = func(*args, **kargs)
            for child in offspring:
                for i in range(len(child)):
                    if child[i] > maxs[i]:
                        child[i] = maxs[i]
                    elif child[i] < mins[i]:
                        child[i] = mins[i]
            return offspring
        return wrapper
    return decorator

# (Not used) makes sure strategy is within bounds
def checkStrategy(minstrategy):
    def decorator(func):
        def wrappper(*args, **kargs):
            children = func(*args, **kargs)
            for child in children:
                for i, s in enumerate(child.strategy):
                    if s < minstrategy:
                        child.strategy[i] = minstrategy
            return children
        return wrappper
    return decorator


toolbox.register("evaluate", evaluate)
# toolbox.register("mate", tools.cxESBlend, alpha=0.5)
# toolbox.register("mutate", tools.mutESLogNormal, c=1, indpb=0.5)
# toolbox.register("mate", tools.cxTwoPoint) # We don't use crossover

# Mutate function draws from normal distribution with mean mu and std sigma
# Each parameter within an indibidual is mutated with indpb chance
toolbox.register("mutate", tools.mutGaussian,
                 mu=0.0, sigma=SIGMA, indpb=INDPB)  
# Population is selected by drawing tournsize individuals at random, and keeping the best one, NPOP times
toolbox.register("select", tools.selTournament, tournsize=TournamentSize)

# toolbox.decorate("mate",  checkBounds(MINS, MAXS))
toolbox.decorate("mutate", checkBounds(MINS, MAXS))


def printStats(fits, length, title):
    mean = sum(fits) / length
    sum2 = sum(x*x for x in fits)
    std = abs(sum2 / length - mean**2)**0.5

    print("  {0} Min {1}".format(title, min(fits)))
    print("  {0} Max {1}".format(title, max(fits)))
    print("  {0} Avg {1}".format(title, mean))
    print("  {0} Std {1}".format(title, std))

# Create multiprocessing pool
if __name__ == '__main__':
    pool = multiprocessing.Pool()
    toolbox.register("map", pool.map)

# Plots a graph of the population according to one of the 3 metrics and one parameter
def plotLogbook(scoreName, paramName):
    plotName = plotDirectory + "/" + scoreName + "_vs_" + paramName + ".png"
    fig, ax1 = plt.subplots()
    gen = logbook.chapters[paramName].select("gen")
    # ax1.set_xticks(range(len(gen) + 1))
    scoresMax = logbook.chapters[scoreName].select("max")
    scoresMin = logbook.chapters[scoreName].select("min")
    line1 = ax1.plot(gen, scoresMax, "b-", label="max" + scoreName)
    line5 = ax1.plot(gen, scoresMin, "b--", label="min" + scoreName)
    ax1.set_xlabel("Generation")
    ax1.set_ylabel(scoreName, color="b")
    for tl in ax1.get_yticklabels():
        tl.set_color("b")

    ax2 = ax1.twinx()
    param_max = logbook.chapters[paramName].select("max")
    param_min = logbook.chapters[paramName].select("min")
    param_avg = logbook.chapters[paramName].select("avg")
    for i in range(len(param_max)):
        param_max[i] *= NAME_TO_FACTOR[paramName]
        param_min[i] *= NAME_TO_FACTOR[paramName]
        param_avg[i] *= NAME_TO_FACTOR[paramName]
    line2 = ax2.plot(gen, param_max, "r-", label="max")
    line3 = ax2.plot(gen, param_avg, "r:", label="avg")
    line4 = ax2.plot(gen, param_min, "r--", label="min")
    ax2.set_ylabel(paramName, color="r")
    for tl in ax2.get_yticklabels():
        tl.set_color("r")

    lns = line1 + line2 + line3 + line4 + line5
    labs = [l.get_label() for l in lns]
    ax1.legend(lns, labs, loc="best")
    plt.tight_layout()
    plt.savefig(plotName)
    plt.close(fig)

# Plots a graph of the best individual according to one of the 3 metrics and one parameter
# HOF = Hall Of Fame, records best indiviual over totallity of training so far
def plotHOF(scoreName, scores, paramName, paramValues):
    plotName = plotDirectory + "/" + "hof_" + scoreName + "_vs_" + paramName + ".png"
    fig, ax1 = plt.subplots()
    gen = logbook.chapters[paramName].select("gen")
    line1 = ax1.plot(gen, scores, "b-", label="best " + scoreName)
    ax1.set_xlabel("Generation")
    ax1.set_ylabel(scoreName, color="b")
    for tl in ax1.get_yticklabels():
        tl.set_color("b")

    ax2 = ax1.twinx()
    line2 = ax2.plot(gen, paramValues, "r-", label=paramName)
    ax2.set_ylabel(paramName, color="r")
    for tl in ax2.get_yticklabels():
        tl.set_color("r")

    lns = line1 + line2
    labs = [l.get_label() for l in lns]
    ax1.legend(lns, labs, loc="best")
    plt.tight_layout()
    plt.savefig(plotName)
    plt.close(fig)

# Objects to keep track of Hall Of Fame (HOF) data
efficiencies = []
fakeRateList = []
dupRateList = []
sigmaScats = []
maxPts = []
impactMaxs = []
maxSeedsPerSpMs = []
#collisionRegionMaxs = []
radLengthPerSeeds = []
deltaRMins = []
deltaRMaxs = []
def main():
    #{'maxPt': 30000, 'impactMax': 1.1,
    #              'deltaRMin': .25, 'sigmaScattering': 4, 'deltaRMax': 60.0, 'maxSeedsPerSpM': 1,'radLengthPerSeed': 0.0023}
    # Objects that will compile the data for population graphs
    logbook = tools.Logbook()
    stats_eff = tools.Statistics(key=lambda ind: ind.fitness.values[0])
    stats_fake = tools.Statistics(key=lambda ind: ind.fitness.values[1])
    stats_dup = tools.Statistics(key=lambda ind: ind.fitness.values[2])
    stats_sigmaScattering = tools.Statistics(
        key=lambda ind: ind[NAME_TO_INDEX["sigmaScattering"]])
    stats_maxSeedsPerSPM = tools.Statistics(
        key=lambda ind: ind[NAME_TO_INDEX["maxSeedsPerSpM"]])
    stats_maxPt = tools.Statistics(key=lambda ind: ind[NAME_TO_INDEX["maxPt"]])
    #stats_collisionRegionMax = tools.Statistics(
    #    key=lambda ind: ind[NAME_TO_INDEX["collisionRegionMax"]])
    stats_impactMax = tools.Statistics(
        key=lambda ind: ind[NAME_TO_INDEX["impactMax"]])
    #stats_collisionRegionMin = tools.Statistics(
    #    key=lambda ind: ind[NAME_TO_INDEX["collisionRegionMin"]])
    stats_deltaRMin = tools.Statistics(key=lambda ind: ind[NAME_TO_INDEX["deltaRMin"]])
    stats_deltaRMax = tools.Statistics(key=lambda ind: ind[NAME_TO_INDEX["deltaRMax"]])
    stats_radLengthPerSeed = tools.Statistics(key=lambda ind: ind[NAME_TO_INDEX["radLengthPerSeed"]])
    mstats = tools.MultiStatistics(Efficiency=stats_eff, FakeRate=stats_fake, DuplicateRate=stats_dup, sigmaScattering=stats_sigmaScattering,
                                   maxSeedsPerSpM=stats_maxSeedsPerSPM, maxPt=stats_maxPt, impactMax=stats_impactMax, deltaRMax=stats_deltaRMax, deltaRMin=stats_deltaRMin,
                                   radLengthPerSeed = stats_radLengthPerSeed)
                                   #collisionRegionMax=stats_collisionRegionMax, collisionRegionMin=stats_collisionRegionMin, impactMax=stats_impactMax, deltaRMax=stats_deltaRMax, deltaRMin=stats_deltaRMin)
    mstats.register("avg", np.mean)
    mstats.register("std", np.std)
    mstats.register("min", np.min)
    mstats.register("max", np.max)

    hof = tools.HallOfFame(1)
    # initialize NPOP copies of initial guess
    pop = toolbox.population_guess()
    indPrint(pop[0])
    firstFit = toolbox.evaluate(pop[0])
    print(firstFit)
    for ind in pop:
        ind.fitness.values = firstFit
    g = 0
    bestEff = 0
    bestDup = 20
    bestFake = 100
    # Stop condition is that the efficiency is greater than 99.4, duplicate % is less than 60, and fakerate is less than 10%
    # or the number of generations reaches NGEN (100).
    while g < NGEN and ((bestEff < 99.4) or bestDup > 60 or bestFake > 10):
        g = g + 1
        print("-- Generation %i --" % g)
        # Select the next generation individuals
        offspring = toolbox.select(pop, len(pop))
        # Clone the selected individuals
        offspring = list(map(toolbox.clone, offspring))
        # Apply mutation on the offspring
        maxMutants = 16
        mutantsCount = 1
        for mutant in offspring:
            if mutantsCount == maxMutants:
                break
            if random.random() < MUTPB:
                mutantsCount += 1
                toolbox.mutate(mutant)
                del mutant.fitness.values
        # Evaluate the individuals with an invalid fitness (the mutated individuals)
        # need to skip NaN values here
        #for ind in offspring:
        #    print(ind.fitness.wvalues)
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        print(f"Evaluating {len(invalid_ind)} individuals...")
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        toPrint = 0
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
            #print("Fitness values")
            #print(ind.fitness.values)
            if (toPrint < 5 and fit[0] == -1):
                indPrint(ind) # print first 5 individuals that cause seedingalgo to break
        pop[:] = offspring
        hof.update(pop)
        # Gather all the fitnesses in one list and print the stats
        effs = [ind.fitness.values[0] for ind in pop]
        fakeRates = [ind.fitness.values[1] for ind in pop]
        dupRates = [ind.fitness.values[2] for ind in pop]
        length = len(pop)
        mean = sum(effs) / length
        print("Efficiency:")
        printStats(effs, length, "Percent")
        print("Duplicate Rate:")
        printStats(dupRates, length, "Percent")
        print("Fake Rate:")
        printStats(fakeRates, length, "Percent")
        print("The best one so far:", end=" ")

        # record data for analyzing best individual
        for goodOne in hof:
            bestEff = goodOne.fitness.values[0]
            efficiencies.append(bestEff)
            sigmaScats.append(
                goodOne[NAME_TO_INDEX['sigmaScattering']] * NAME_TO_FACTOR["sigmaScattering"])
            maxPts.append(goodOne[NAME_TO_INDEX['maxPt']] * NAME_TO_FACTOR["maxPt"])
            impactMaxs.append(goodOne[NAME_TO_INDEX["impactMax"]] * NAME_TO_FACTOR["impactMax"])
            maxSeedsPerSpMs.append(int(goodOne[NAME_TO_INDEX["maxSeedsPerSpM"]] * NAME_TO_FACTOR["maxSeedsPerSpM"]))
            #collisionRegionMaxs.append(goodOne[NAME_TO_INDEX["collisionRegionMax"]] * NAME_TO_FACTOR["collisionRegionMax"])
            deltaRMaxs.append(goodOne[NAME_TO_INDEX["deltaRMax"]] * NAME_TO_FACTOR["deltaRMax"])
            deltaRMins.append(goodOne[NAME_TO_INDEX["deltaRMin"]] * NAME_TO_FACTOR["deltaRMin"])
            radLengthPerSeeds.append(goodOne[NAME_TO_INDEX["radLengthPerSeed"]]*NAME_TO_FACTOR["radLengthPerSeed"])
            
            bestFake = goodOne.fitness.values[1]
            fakeRateList.append(bestFake)
            bestDup = goodOne.fitness.values[2]
            dupRateList.append(bestDup)
            indPrint(goodOne)
            print("Best score (eff score, fakeRate, dupRate):", end=" ")
            print(goodOne.fitness.values)
        # record data for analyzing the population
        logbook.record(gen=g, **mstats.compile(pop))
    return logbook, hof


if (len(MINS) != len(MAXS)) or len(NAME_TO_FACTOR) != len(MINS):
    print("Mismatched definition of names_to_factor and/or mins maxs")

logbook, hof = main()

if (not os.path.isdir(plotDirectory)):
    os.mkdir(plotDirectory)
# Make plots for the population
for name in NAME_TO_FACTOR:
    plotLogbook("Efficiency", name)
    plotLogbook("DuplicateRate", name)
    plotLogbook("FakeRate", name)
# Make plots for the best individual
plotHOF("Efficiency", efficiencies, "sigmaScattering", sigmaScats)
plotHOF("Efficiency", efficiencies, "maxPt", maxPts)
plotHOF("Efficiency", efficiencies, "deltaRMin", deltaRMins)
plotHOF("Efficiency", efficiencies, "deltaRMax", deltaRMaxs)
plotHOF("DuplicateRate", dupRateList, "sigmaScattering", sigmaScats)
plotHOF("FakeRate", fakeRateList, "sigmaScattering", sigmaScats)
plotHOF("DuplicateRate", dupRateList, "maxSeedsPerSpM", maxSeedsPerSpMs)
plotHOF("FakeRate", fakeRateList, "maxSeedsPerSpM", maxSeedsPerSpMs)
with open('bad_input_test','wb') as fp:
    pickle.dump(bad_params,fp)
