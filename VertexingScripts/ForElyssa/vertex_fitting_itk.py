#!/usr/bin/env python3
from pathlib import Path
from typing import Optional, Union
import argparse
import sys
import os
import enum
import warnings
from collections import namedtuple


from acts.examples import (
    Sequencer,
    ParticleSelector,
    ParticleSmearing,
    TruthVertexFinder,
    VertexFitterAlgorithm,
    IterativeVertexFinderAlgorithm,
    RootParticleReader,
    AdaptiveMultiVertexFinderAlgorithm,
    RootVertexPerformanceWriter,
    RootTrajectorySummaryReader,
    TrackSelector,
    GenericDetector,
)

import acts
import itk

from acts import UnitConstants as u

import pythia8

class VertexFinder(enum.Enum):
    Truth = (1,)
    AMVF = (2,)
    Iterative = (3,)

def getArgumentParser():
    """ Get arguments from command line"""
    parser = argparse.ArgumentParser(description="CKF arguments")
    parser.add_argument('-i',
                        '--indir',
                        dest='indir',
                        help='Directory with input root files',
                        default = 'data')
    parser.add_argument('-itr',
                        '--intracksdir',
                        dest='intracksdir',
                        help='Directory with input tracksummary files',
                        default = 'tracks')
    parser.add_argument('-o',
                        '--output',
                        dest='outdir',
                        help='Output directory for new ntuples',
                        default='outdir')
    parser.add_argument('-n',
                        '--nEvents',
                        dest='nEvts',
                        help='Number of events to run over',
                        default='10')
    parser.add_argument('-tMZ',
                        '--tracksMaxZinterval',
                        dest='tracksMaxZinterval',
                        help='AMVF : tracksMaxZinterval',
                        default='3.0')
    parser.add_argument('-tMS',
                        '--tracksMaxSignificance',
                        dest='tracksMaxSignificance',
                        help='AMVF: tracksMaxSignificance',
                        default='5.0')
    parser.add_argument('-mVChi2',
                        '--maxVertexChi2',
                        dest='maxVertexChi2',
                        help='AMVF: maxVertexChi2',
                        default='18.42')
    parser.add_argument('-mMVS',
                        '--maxMergeVertexSignificance',
                        dest='maxMergeVertexSignificance',
                        help='AMVF: maxMergeVertexSignificance',
                        default='3.0')
    parser.add_argument('-mW',
                        '--minWeight',
                        dest='minWeight',
                        help='AMVF: minWeight',
                        default='0.0001')
    parser.add_argument('-mIt',
                        '--maxIterations',
                        dest='maxIterations',
                        help='AMVF: maxIterations',
                        default='100')
    parser.add_argument('-mVC',
                        '--maximumVertexContamination',
                        dest='maximumVertexContamination',
                        help='AMVF: maximumVertexContamination',
                        default='0.5')

    return parser

def addVertexFitting(
    s,
    field,
    outputDirRoot: Optional[Union[Path, str]] = None,
    associatedParticles: str = "associatedTruthParticles",
    vertexFinder: VertexFinder = VertexFinder.Truth,
    logLevel: Optional[acts.logging.Level] = None,
    v_TracksMaxZinterval=3.,
    v_TracksMaxSignificance=5.,
    v_MaxVertexChi2=18.42,
    v_MaxMergeVertexSignificance=3.,
    v_MinWeight=0.0001,
    v_MaxIterations=100,
    v_MaximumVertexContamination=0.5,
):
    """This function steers the vertex fitting

    Parameters
    ----------
    s: Sequencer
        the sequencer module to which we add the Seeding steps (returned from addVertexFitting)
    field : magnetic field
    outputDirRoot : Path|str, path, None
        the output folder for the Root output, None triggers no output
    associatedParticles : str, "associatedTruthParticles"
        RootVertexPerformanceWriter.inputAssociatedTruthParticles
    vertexFinder : VertexFinder, Truth
        vertexFinder algorithm: one of Truth, AMVF, Iterative
    logLevel : acts.logging.Level, None
        logging level to override setting given in `s`
    """

    def customLogLevel(custom: acts.logging.Level = acts.logging.INFO):
        """override logging level"""
        if logLevel is None:
            return s.config.logLevel
        return acts.logging.Level(max(custom.value, logLevel.value))

    if int(customLogLevel()) <= int(acts.logging.DEBUG):
        acts.examples.dump_args_calls(locals())

    inputParticles = "particles_input"
    outputVertices = "fittedVertices"
    selectedParticles = "particles_selected"
    trackParameters = "trackparameters"
    trackParametersNocut = "trackparameters_nocut"

    outputTime = ""
    if vertexFinder == VertexFinder.Truth:
        findVertices = TruthVertexFinder(
            level=customLogLevel(acts.logging.VERBOSE),
            inputParticles=selectedParticles,
            outputProtoVertices="protovertices",
            excludeSecondaries=True,
        )
        s.addAlgorithm(findVertices)
        fitVertices = VertexFitterAlgorithm(
            level=customLogLevel(acts.logging.VERBOSE),
            bField=field,
            inputTrackParameters=trackParameters,
            inputProtoVertices=findVertices.config.outputProtoVertices,
            outputVertices=outputVertices,
        )
        s.addAlgorithm(fitVertices)

    elif vertexFinder == VertexFinder.Iterative:
        findVertices = IterativeVertexFinderAlgorithm(
            level=customLogLevel(),
            bField=field,
            inputTrackParameters=trackParameters,
            outputProtoVertices="protovertices",
            outputVertices=outputVertices,
        )
        s.addAlgorithm(findVertices)
    elif vertexFinder == VertexFinder.AMVF:
        outputTime = "outputTime"
        findVertices = AdaptiveMultiVertexFinderAlgorithm(
            level=customLogLevel(),
            bField=field,
            inputTrackParameters=trackParameters,
            outputProtoVertices="protovertices",
            outputVertices=outputVertices,
            outputTime=outputTime,
            amvf_useBeamSpotConstraint=False,
            amvf_tracksMaxZinterval=float(v_TracksMaxZinterval) * u.mm, 
            amvf_tracksMaxSignificance=float(v_TracksMaxSignificance),
            amvf_maxVertexChi2=float(v_MaxVertexChi2),
            amvf_maxMergeVertexSignificance=float(v_MaxMergeVertexSignificance),
            amvf_minWeight=float(v_MinWeight),
            amvf_maxIterations=int(v_MaxIterations),
            amvf_maximumVertexContamination=float(v_MaximumVertexContamination),
            amvf_useVertexCovForIPEstimation=False,
        )

        s.addAlgorithm(findVertices)
    else:
        raise RuntimeError("Invalid finder argument")

    if outputDirRoot is not None:
        outputDirRoot = Path(outputDirRoot)
        if not outputDirRoot.exists():
            outputDirRoot.mkdir()
        if associatedParticles == selectedParticles:
            warnings.warn(
                "Using RootVertexPerformanceWriter with smeared particles is not necessarily supported. "
                "Please get in touch with us"
            )
        s.addWriter(
            RootVertexPerformanceWriter(
                level=customLogLevel(),
                inputAllTruthParticles=inputParticles,
                inputSelectedTruthParticles=selectedParticles,
                inputAssociatedTruthParticles=associatedParticles,
                inputFittedTracks=trackParameters,
                inputVertices=outputVertices,
                inputTime=outputTime,
                treeName="vertexing",
                filePath=str(outputDirRoot / "performance_vertexing.root"),
            )
        )

    return s


def runVertexFitting(
    field,
    outputDir: Path,
    outputRoot: bool = True,
    inputParticlePath: Optional[Path] = None,
    inputTrackSummary: Path = None,
    NumEvents=10,
    TracksMaxZinterval=3.,
    TracksMaxSignificance=5.,
    MaxVertexChi2=18.42,
    MaxMergeVertexSignificance=3.,
    MinWeight=0.0001,
    MaxIterations=100,
    MaximumVertexContamination=0.5,
    vertexFinder: VertexFinder = VertexFinder.Truth,
    s=None,
):
    s = s or Sequencer(events=int(NumEvents), numThreads=-1)

    logger = acts.logging.getLogger("VertexFittingExample")

    rnd = acts.examples.RandomNumbers(seed=42)

    inputParticles = "particles_input"
    if inputParticlePath is None:
        logger.info("Generating particles using Pythia8")
        pythia8.addPythia8(s, rnd)
    else:
        logger.info("Reading particles from %s", inputParticlePath.resolve())
        assert inputParticlePath.exists()
        s.addReader(
            RootParticleReader(
                level=acts.logging.INFO,
                filePath=str(inputParticlePath.resolve()),
                particleCollection=inputParticles,
                orderedEvents=False,
            )
        )

    selectedParticles = "particles_selected"
    ptclSelector = ParticleSelector(
        level=acts.logging.INFO,
        inputParticles=inputParticles,
        outputParticles=selectedParticles,
        removeNeutral=True,
        absEtaMax=4.0,
        rhoMax=4.0 * u.mm,
        ptMin=900 * u.MeV,
    )
    s.addAlgorithm(ptclSelector)

    trackParameters = "trackparameters"
    trackParametersNocut = "trackparameters_nocut"
    if inputTrackSummary is None or inputParticlePath is None:
        logger.info("Using smeared particles")

        ptclSmearing = ParticleSmearing(
            level=acts.logging.INFO,
            inputParticles=selectedParticles,
            outputTrackParameters=trackParameters,
            randomNumbers=rnd,
        )
        s.addAlgorithm(ptclSmearing)
        trackParametersNocut = trackParameters
        associatedParticles = selectedParticles
    else:
        logger.info("Reading track summary from %s", inputTrackSummary.resolve())
        assert inputTrackSummary.exists()
        associatedParticles = "associatedTruthParticles"

        trackSummaryReader = RootTrajectorySummaryReader(
            level=acts.logging.VERBOSE,
            outputTracks=trackParameters, #"fittedTrackParameters",
            outputParticles=associatedParticles,
            filePath=str(inputTrackSummary.resolve()),
            orderedEvents=False,
        )
        s.addReader(trackSummaryReader)

        '''
        s.addAlgorithm(
            TrackSelector(
                level=acts.logging.INFO,
                inputTrackParameters=trackSummaryReader.config.outputTracks,
                outputTrackParameters=trackParameters,
                outputTrackIndices="outputTrackIndices",
                removeNeutral=True,
                absEtaMax=2.5,
                loc0Max=4.0 * u.mm,  # rho max
                ptMin=500 * u.MeV,
            )
        )
        '''
        

    logger.info("Using vertex finder: %s", vertexFinder.name)

    return addVertexFitting(
        s,
        field,
        outputDirRoot=outputDir if outputRoot else None,
        associatedParticles=associatedParticles,
        vertexFinder=vertexFinder,
        v_TracksMaxZinterval=TracksMaxZinterval,
        v_TracksMaxSignificance=TracksMaxSignificance,
        v_MaxVertexChi2=MaxVertexChi2,
        v_MaxMergeVertexSignificance=MaxMergeVertexSignificance,
        v_MinWeight=MinWeight,
        v_MaxIterations=MaxIterations,
        v_MaximumVertexContamination=MaximumVertexContamination,
    )


if "__main__" == __name__:
    options = getArgumentParser().parse_args()

    Inputdir = options.indir
    Outputdir = options.outdir
    InTracksDir = options.intracksdir

    geo_dir = Path(__file__).resolve().parent.parent / "acts-detector-examples"

    #detector, trackingGeometry, decorators = itk.buildITkGeometry(geo_dir)

    field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))

    inputParticlePath = Path(Inputdir) / "particles.root"
    if not inputParticlePath.exists():
        inputParticlePath = None

    inputTrackSummary = None
    for p in ("tracksummary_fitter.root", "tracksummary_ckf.root"):
        p = Path(InTracksDir) / p
        if p.exists():
            inputTrackSummary = p
            break

    runVertexFitting(
        field,
        outputDir=Outputdir,
        vertexFinder=VertexFinder.AMVF,
        inputParticlePath=inputParticlePath,
        inputTrackSummary=inputTrackSummary,
        NumEvents=options.nEvts,
        TracksMaxZinterval=options.tracksMaxZinterval,
        TracksMaxSignificance=options.tracksMaxSignificance,
        MaxVertexChi2=options.maxVertexChi2,
        MaxMergeVertexSignificance=options.maxMergeVertexSignificance,
        MinWeight=options.minWeight,
        MaxIterations=options.maxIterations,
        MaximumVertexContamination=options.maximumVertexContamination,
    ).run()
    
