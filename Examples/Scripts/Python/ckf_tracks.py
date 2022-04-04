#!/usr/bin/env python3
from pathlib import Path
from typing import Optional, Union

from acts.examples import Sequencer, GenericDetector, RootParticleReader

import acts

from acts import UnitConstants as u
<<<<<<< HEAD
import argparse
=======
from seeding import TruthSeedRanges


@acts.examples.NamedTypeArgs(
    truthSeedRanges=TruthSeedRanges,
)
def addCKFTracks(
    s: acts.examples.Sequencer,
    trackingGeometry: acts.TrackingGeometry,
    field: acts.MagneticFieldProvider,
    truthSeedRanges: TruthSeedRanges = TruthSeedRanges(),
    outputDirCsv: Optional[Union[Path, str]] = None,
    outputDirRoot: Optional[Union[Path, str]] = None,
    selectedParticles: str = "truth_seeds_selected",
) -> acts.examples.Sequencer:
    """This function steers the seeding

    Parameters
    ----------
    s: Sequencer
        the sequencer module to which we add the Seeding steps (returned from addSeeding)
    trackingGeometry : tracking geometry
    field : magnetic field
    truthSeedRanges : TruthSeedRanges(nHits, pt)
        CKFPerformanceWriter configuration. Each range is specified as a tuple of (min,max), though currently only the min is used.
        Defaults specified in Examples/Io/Performance/ActsExamples/Io/Performance/CKFPerformanceWriter.hpp
    outputDirCsv : Path|str, path, None
        the output folder for the Csv output, None triggers no output
    outputDirRoot : Path|str, path, None
        the output folder for the Root output, None triggers no output
    selectedParticles : str, "truth_seeds_selected"
        CKFPerformanceWriter truth input
    """

    if int(s.config.logLevel) <= int(acts.logging.DEBUG):
        acts.examples.dump_args_calls(locals())

    # Setup the track finding algorithm with CKF
    # It takes all the source links created from truth hit smearing, seeds from
    # truth particle smearing and source link selection config
    trackFinder = acts.examples.TrackFindingAlgorithm(
        level=s.config.logLevel,
        measurementSelectorCfg=acts.MeasurementSelector.Config(
            [(acts.GeometryIdentifier(), ([], [15.0], [10]))]
        ),
        inputMeasurements="measurements",
        inputSourceLinks="sourcelinks",
        inputInitialTrackParameters="estimatedparameters",
        outputTrajectories="trajectories",
        findTracks=acts.examples.TrackFindingAlgorithm.makeTrackFinderFunction(
            trackingGeometry, field
        ),
    )
    s.addAlgorithm(trackFinder)

    if outputDirRoot is not None:
        outputDirRoot = Path(outputDirRoot)
        if not outputDirRoot.exists():
            outputDirRoot.mkdir()

        # write track states from CKF
        trackStatesWriter = acts.examples.RootTrajectoryStatesWriter(
            level=s.config.logLevel,
            inputTrajectories=trackFinder.config.outputTrajectories,
            # @note The full particles collection is used here to avoid lots of warnings
            # since the unselected CKF track might have a majority particle not in the
            # filtered particle collection. This could be avoided when a seperate track
            # selection algorithm is used.
            inputParticles="particles_selected",
            inputSimHits="simhits",
            inputMeasurementParticlesMap="measurement_particles_map",
            inputMeasurementSimHitsMap="measurement_simhits_map",
            filePath=str(outputDirRoot / "trackstates_ckf.root"),
            treeName="trackstates",
        )
        s.addWriter(trackStatesWriter)

        # write track summary from CKF
        trackSummaryWriter = acts.examples.RootTrajectorySummaryWriter(
            level=s.config.logLevel,
            inputTrajectories=trackFinder.config.outputTrajectories,
            # @note The full particles collection is used here to avoid lots of warnings
            # since the unselected CKF track might have a majority particle not in the
            # filtered particle collection. This could be avoided when a seperate track
            # selection algorithm is used.
            inputParticles="particles_selected",
            inputMeasurementParticlesMap="measurement_particles_map",
            filePath=str(outputDirRoot / "tracksummary_ckf.root"),
            treeName="tracksummary",
        )
        s.addWriter(trackSummaryWriter)

        # Write CKF performance data
        ckfPerfWriter = acts.examples.CKFPerformanceWriter(
            level=s.config.logLevel,
            inputParticles=selectedParticles,
            inputTrajectories=trackFinder.config.outputTrajectories,
            inputMeasurementParticlesMap="measurement_particles_map",
            # The bottom seed could be the first, second or third hits on the truth track
            nMeasurementsMin=truthSeedRanges.nHits[0],
            ptMin=truthSeedRanges.pt[0],
            filePath=str(outputDirRoot / "performance_ckf.root"),
        )
        s.addWriter(ckfPerfWriter)

    if outputDirCsv is not None:
        outputDirCsv = Path(outputDirCsv)
        if not outputDirCsv.exists():
            outputDirCsv.mkdir()
        acts.logging.getLogger("CKFExample").info("Writing CSV files")
        csvMTJWriter = acts.examples.CsvMultiTrajectoryWriter(
            level=s.config.logLevel,
            inputTrajectories=trackFinder.config.outputTrajectories,
            inputMeasurementParticlesMap="measurement_particles_map",
            outputDir=str(outputDirCsv),
        )
        s.addWriter(csvMTJWriter)

    return s
>>>>>>> b7d70c4ae0b68888aae7abcf9db374d5ae451242


def runCKFTracks(
    trackingGeometry,
    decorators,
    geometrySelection: Path,
    digiConfigFile: Path,
    field,
    outputDir: Path,
    truthSmearedSeeded=False,
    truthEstimatedSeeded=False,
    outputCsv=True,
    inputParticlePath: Optional[Path] = None,
    s=None,
):
<<<<<<< HEAD

    s = s or Sequencer(events=10, numThreads=-1)
=======
>>>>>>> b7d70c4ae0b68888aae7abcf9db374d5ae451242

    from particle_gun import addParticleGun, EtaConfig, PhiConfig, ParticleConfig
    from fatras import addFatras
    from digitization import addDigitization
    from seeding import (
        addSeeding,
        TruthSeedRanges,
        ParticleSmearingSigmas,
        SeedfinderConfigArg,
        SeedingAlgorithm,
        TrackParamsEstimationConfig,
    )

    s = s or acts.examples.Sequencer(
        events=100, numThreads=-1, logLevel=acts.logging.INFO
    )
    for d in decorators:
        s.addContextDecorator(d)
    rnd = acts.examples.RandomNumbers(seed=42)
    outputDir = Path(outputDir)

    if inputParticlePath is None:
        s = addParticleGun(
            s,
            EtaConfig(-2.0, 2.0),
            ParticleConfig(4, acts.PdgParticle.eMuon, True),
            PhiConfig(0.0, 360.0 * u.degree),
            multiplicity=2,
            rnd=rnd,
        )
    else:
        acts.logging.getLogger("CKFExample").info(
            "Reading particles from %s", inputParticlePath.resolve()
        )
        assert inputParticlePath.exists()
        s.addReader(
            RootParticleReader(
                level=acts.logging.INFO,
                filePath=str(inputParticlePath.resolve()),
                particleCollection="particles_input",
                orderedEvents=False,
            )
        )

    s = addFatras(
        s,
        trackingGeometry,
        field,
        rnd=rnd,
    )

    s = addDigitization(
        s,
        trackingGeometry,
        field,
        digiConfigFile=digiConfigFile,
        rnd=rnd,
    )

<<<<<<< HEAD
    inputParticles = selAlg.config.outputParticles

    # Create starting parameters from either particle smearing or combined seed
    # finding and track parameters estimation
    if truthSmearedSeeded:
        logger.info("Using smeared truth particles for seeding")
        # Run particle smearing
        ptclSmear = acts.examples.ParticleSmearing(
            level=acts.logging.INFO,
            inputParticles=inputParticles,
            outputTrackParameters="smearedparameters",
            randomNumbers=rnd,
            # gaussian sigmas to smear particle parameters
            sigmaD0=20 * u.um,
            sigmaD0PtA=30 * u.um,
            sigmaD0PtB=0.3 / 1 * u.GeV,
            sigmaZ0=20 * u.um,
            sigmaZ0PtA=30 * u.um,
            sigmaZ0PtB=0.3 / 1 * u.GeV,
            sigmaPhi=1 * u.degree,
            sigmaTheta=1 * u.degree,
            sigmaPRel=0.01,
            sigmaT0=1 * u.ns,
            initialVarInflation=[1, 1, 1, 1, 1, 1],
        )
        outputTrackParameters = ptclSmear.config.outputTrackParameters
        s.addAlgorithm(ptclSmear)
    else:
        # Create space points
        spAlg = acts.examples.SpacePointMaker(
            level=acts.logging.INFO,
            inputSourceLinks=digiAlg.config.outputSourceLinks,
            inputMeasurements=digiAlg.config.outputMeasurements,
            outputSpacePoints="spacepoints",
            trackingGeometry=trackingGeometry,
            geometrySelection=acts.examples.readJsonGeometryList(
                str(geometrySelection)
            ),
        )
        s.addAlgorithm(spAlg)

        # Run either: truth track finding or seeding
        if truthEstimatedSeeded:
            logger.info("Using truth track finding from space points for seeding")
            # Use truth tracking
            truthTrackFinder = acts.examples.TruthTrackFinder(
                level=acts.logging.INFO,
                inputParticles=inputParticles,
                inputMeasurementParticlesMap=digiAlg.config.outputMeasurementParticlesMap,
                outputProtoTracks="prototracks",
            )
            s.addAlgorithm(truthTrackFinder)
            inputProtoTracks = truthTrackFinder.config.outputProtoTracks
            inputSeeds = ""
        else:
            logger.info("Using seeding")
            # Use seeding
            gridConfig = acts.SpacePointGridConfig(
                bFieldInZ=1.99724 * u.T,
                minPt=args.sf_minPt * u.MeV,
                rMax=args.sf_rMax * u.mm,
                zMax=args.sf_zMax * u.mm,
                zMin=args.sf_zMin * u.mm,
                deltaRMax=args.sf_deltaRMax * u.mm,
                cotThetaMax=args.sf_cotThetaMax  # 2.7 eta
            )

            seedFilterConfig = acts.SeedFilterConfig(
                maxSeedsPerSpM=args.sf_maxSeedsPerSpM, deltaRMin=args.sf_deltaRMin * u.mm
            )

            seedFinderConfig = acts.SeedfinderConfig(
                rMax=gridConfig.rMax,
                deltaRMin=seedFilterConfig.deltaRMin,
                deltaRMax=gridConfig.deltaRMax,
                deltaRMinTopSP=seedFilterConfig.deltaRMin,
                deltaRMinBottomSP=seedFilterConfig.deltaRMin,
                deltaRMaxTopSP=gridConfig.deltaRMax,
                deltaRMaxBottomSP=gridConfig.deltaRMax,
                collisionRegionMin=args.sf_collisionRegionMin * u.mm,
                collisionRegionMax=args.sf_collisionRegionMax * u.mm,
                zMin=gridConfig.zMin,
                zMax=gridConfig.zMax,
                maxSeedsPerSpM=seedFilterConfig.maxSeedsPerSpM,
                cotThetaMax=gridConfig.cotThetaMax,
                sigmaScattering=args.sf_sigmaScattering,
                radLengthPerSeed=args.sf_radLengthPerSeed,
                minPt=gridConfig.minPt,
                bFieldInZ=gridConfig.bFieldInZ,
                beamPos=acts.Vector2(0 * u.mm, 0 * u.mm),
                impactMax=args.sf_impactMax * u.mm,
                maxPtScattering = args.sf_maxPtScattering*u.MeV,
                sigmaError = args.sf_sigmaError,
            )
            seeding = acts.examples.SeedingAlgorithm(
                level=acts.logging.INFO,
                inputSpacePoints=[spAlg.config.outputSpacePoints],
                outputSeeds="seeds",
                outputProtoTracks="prototracks",
                gridConfig=gridConfig,
                seedFilterConfig=seedFilterConfig,
                seedFinderConfig=seedFinderConfig,
            )
            s.addAlgorithm(seeding)
            inputProtoTracks = seeding.config.outputProtoTracks
            inputSeeds = seeding.config.outputSeeds

        # Write truth track finding / seeding performance
        trackFinderPerformanceWriter = acts.examples.TrackFinderPerformanceWriter(
            level=acts.logging.INFO,
            inputProtoTracks=inputProtoTracks,
            inputParticles=inputParticles,  # the original selected particles after digitization
            inputMeasurementParticlesMap=digiAlg.config.outputMeasurementParticlesMap,
            filePath=str(outputDir / "performance_seeding_trees.root"),
        )
        s.addWriter(trackFinderPerformanceWriter)

        # Estimate track parameters from seeds
        paramEstimation = acts.examples.TrackParamsEstimationAlgorithm(
            level=acts.logging.INFO,
            inputSeeds=inputSeeds,
            inputProtoTracks=inputProtoTracks,
            inputSpacePoints=[spAlg.config.outputSpacePoints],
            inputSourceLinks=digiCfg.outputSourceLinks,
            outputTrackParameters="estimatedparameters",
            outputProtoTracks="prototracks_estimated",
            trackingGeometry=trackingGeometry,
            magneticField=field,
            bFieldMin=0.1 * u.T,
            deltaRMax=100.0 * u.mm,
            deltaRMin=10.0 * u.mm,
            sigmaLoc0=25.0 * u.um,
            sigmaLoc1=100.0 * u.um,
            sigmaPhi=0.02 * u.degree,
            sigmaTheta=0.02 * u.degree,
            sigmaQOverP=0.1 / 1.0 * u.GeV,
            sigmaT0=1400.0 * u.s,
            initialVarInflation=[1, 1, 1, 1, 1, 1],
        )
        s.addAlgorithm(paramEstimation)
        outputTrackParameters = paramEstimation.config.outputTrackParameters

    # Setup the track finding algorithm with CKF
    # It takes all the source links created from truth hit smearing, seeds from
    # truth particle smearing and source link selection config
    trackFinder = acts.examples.TrackFindingAlgorithm(
        level=acts.logging.INFO,
        measurementSelectorCfg=acts.MeasurementSelector.Config(
            [(acts.GeometryIdentifier(), (args.ckf_selection_abseta_bins, args.ckf_selection_chi2max, 
            args.ckf_selection_nmax))]
        ),
        inputMeasurements=digiAlg.config.outputMeasurements,
        inputSourceLinks=digiAlg.config.outputSourceLinks,
        inputInitialTrackParameters=outputTrackParameters,
        outputTrajectories="trajectories",
        findTracks=acts.examples.TrackFindingAlgorithm.makeTrackFinderFunction(
            trackingGeometry, field
=======
    s = addSeeding(
        s,
        trackingGeometry,
        field,
        TruthSeedRanges(pt=(500.0 * u.MeV, None), nHits=(9, None)),
        ParticleSmearingSigmas(pRel=0.01),  # only used by SeedingAlgorithm.TruthSmeared
        SeedfinderConfigArg(
            r=(None, 200 * u.mm),  # rMin=default, 33mm
            deltaR=(1 * u.mm, 60 * u.mm),
            collisionRegion=(-250 * u.mm, 250 * u.mm),
            z=(-2000 * u.mm, 2000 * u.mm),
            maxSeedsPerSpM=1,
            sigmaScattering=50,
            radLengthPerSeed=0.1,
            minPt=500 * u.MeV,
            bFieldInZ=1.99724 * u.T,
            impactMax=3 * u.mm,
>>>>>>> b7d70c4ae0b68888aae7abcf9db374d5ae451242
        ),
        TrackParamsEstimationConfig(deltaR=(10.0 * u.mm, None)),
        seedingAlgorithm=SeedingAlgorithm.TruthSmeared
        if truthSmearedSeeded
        else SeedingAlgorithm.TruthEstimated
        if truthEstimatedSeeded
        else SeedingAlgorithm.Default,
        geoSelectionConfigFile=geometrySelection,
        outputDirRoot=outputDir,
        rnd=rnd,  # only used by SeedingAlgorithm.TruthSmeared
    )

<<<<<<< HEAD
    # write track summary from CKF
    trackSummaryWriter = acts.examples.RootTrajectorySummaryWriter(
        level=acts.logging.INFO,
        inputTrajectories=trackFinder.config.outputTrajectories,
        # @note The full particles collection is used here to avoid lots of warnings
        # since the unselected CKF track might have a majority particle not in the
        # filtered particle collection. This could be avoided when a seperate track
        # selection algorithm is used.
        inputParticles=selector.config.outputParticles,
        inputMeasurementParticlesMap=digiAlg.config.outputMeasurementParticlesMap,
        filePath=str(outputDir / "tracksummary_ckf.root"),
        treeName="tracksummary",
    )
    s.addWriter(trackSummaryWriter)

    # Write CKF performance data
    ckfPerfWriterConfig = acts.examples.CKFPerformanceWriter.Config(
        inputParticles=inputParticles,
        inputTrajectories=trackFinder.config.outputTrajectories,
        inputMeasurementParticlesMap=digiAlg.config.outputMeasurementParticlesMap,
        # The bottom seed could be the first, second or third hits on the truth track
        nMeasurementsMin=selAlg.config.nHitsMin - 3,
        ptMin=0.4 * u.GeV,
        outputIsML = args.outputIsML,
        filePath=str(outputDir / "performance_ckf.root"),
    ) 
    print(ckfPerfWriterConfig)
    ckfPerfWriterConfig.outputIsML = args.outputIsML
    ckfPerfWriter = acts.examples.CKFPerformanceWriter(
        ckfPerfWriterConfig,
        acts.logging.INFO
    )
    #print(ckfPerfWriter.level)
    #print(ckfPerfWriter.outputIsML)
    #ckfPerfWriter.outputIsML = args.outputIsML
    s.addWriter(ckfPerfWriter)

    if outputCsv:
        csv_dir = outputDir / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Writing CSV files")
        csvMTJWriter = acts.examples.CsvMultiTrajectoryWriter(
            level=acts.logging.INFO,
            inputTrajectories=trackFinder.config.outputTrajectories,
            inputMeasurementParticlesMap=digiAlg.config.outputMeasurementParticlesMap,
            outputDir=str(csv_dir),
        )
        s.addWriter(csvMTJWriter)
=======
    s = addCKFTracks(
        s,
        trackingGeometry,
        field,
        TruthSeedRanges(pt=(400.0 * u.MeV, None), nHits=(6, None)),
        outputDirRoot=outputDir,
        outputDirCsv=outputDir / "csv" if outputCsv else None,
    )
>>>>>>> b7d70c4ae0b68888aae7abcf9db374d5ae451242

    return s


if "__main__" == __name__:
    # Insert argument parser dudes
    p = argparse.ArgumentParser(
        description = "Example script to run the generic detector with parameter changes",
    )
    p.add_argument(
        "--sf_minPt",
        default = 500.0,
        type = float,
        help = "Seed finder minimum pT in MeV."
    )

    p.add_argument(
        "--sf_cotThetaMax",
        default = 7.40627,
        type = float,
        help = "cot of maximum theta angle"
    )

    p.add_argument(
        "--sf_deltaRMin",
        default = 1.0,
        type = float,
        help = "Minimum distance in mm between two SPs in a seed"
    )

    p.add_argument(
        "--sf_deltaRMax",
        default = 60.0,
        type = float,
        help = "Maximum distance in mm between two SPs in a seed"
    )

    p.add_argument(
        "--sf_impactMax",
        default = 3.0,
        type = float,
        help = "max impact parameter in mm"
    )

    p.add_argument(
        "--sf_sigmaScattering",
        default = 50.0,
        type = float,
        help = "How many sigmas of scattering to include in seeds"
    )

    p.add_argument(
        "--sf_maxSeedsPerSpM",
        default = 1,
        type = int,
        help = "How many seeds can share one middle SpacePoint"
    )

    p.add_argument(
        "--sf_collisionRegionMin",
        default = -250.0,
        type = float,
        help = "limiting location of collision region in z in mm"
    )

    p.add_argument(
        "--sf_collisionRegionMax",
        default = 250.0,
        type = float,
        help = "limiting location of collision region in z in mm"
    )

    p.add_argument(
        "--sf_zMin",
        default = -2000.0,
        type = float,
        help = "Minimum z of space points included in algorithm"
    )

    p.add_argument(
        "--sf_zMax",
        default = 2000.0,
        type = float,
        help = "Maximum z of space points included in algorithm"
    )

    p.add_argument(
        "--sf_rMax",
        default = 200.0,
        type = float,
        help = "Max radius of Space Points included in algorithm in mm"
    )

    p.add_argument(
        "--sf_rMin",
        default = 33.0,
        type = float,
        help = "Min radius of Space Points included in algorithm in mm"
    )
    # Not adding bFieldInZ or beamPos
    p.add_argument(
        "--sf_maxPtScattering",
        default = 10000.0,
        type = float,
        help = "maximum Pt for scattering cut"
    )

    p.add_argument(
        "--sf_radLengthPerSeed",
        default = 0.1,
        type = float,
        help = "Average radiation length"
    )

    p.add_argument(
        "--output_dir",
        default=Path.cwd(),
        type=Path,
        help="Directory to write outputs to"
    )


    # Get input particles
    p.add_argument(
        "--input_dir",
        default = "input_particles",
        type = Path,
        help = "Input directory"
    )

    # Get other optimization arguments
    p.add_argument(
        "--sf_sigmaError",
        default = 5.0,
        type = float,
        help = "Sigma error with seed finding"
    )

    p.add_argument(
        "--ckf_selection_chi2max",
        default = [15.0],
        type = float,
        nargs = "+",
        help = "Maximum chi2 for CKF measurement selection"
    )

    p.add_argument(
        "--ckf_selection_nmax",
        default = [10],
        type = int,
        nargs = "+",
        help = "Maximum number of measurement candidates on a surface for CKF measurement selection"
    )

    p.add_argument(
        "--ckf_selection_abseta_bins",
        default = [],
        type = float,
        nargs = "+",
        help = "bins in |eta| to specify variable selections"
    )

    p.add_argument(
        "--outputIsML",
        default = True,
        type = bool,
        help = "Prints formatted output for Optuna/optimization algs if true"
    )

    p.add_argument(
        "--digi_config_file",
        default = "/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/Digitization/share/default-smearing-config-generic.json",
        help = "Digi config file" 
    )

    p.add_argument(
        "--geo_selection_config_file",
        default = "/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/TrackFinding/share/geoSelection-genericDetector.json",
        #type = Path,
        help = "Geo config file"
    )

    # Make output directory
    args = p.parse_args()
    outdir = args.output_dir
    args.output_dir.mkdir(exist_ok=True, parents=True)

    ## Make sure that selection lists are the same length
    #assert len(args.ckf_selection_abseta_bins) == len(args.ckf_selection_nmax) == len(args.ckf_selection_abseta_bins), "Selection parameters must be the same length"

    ## TO DO: put new parameters in algorithms above and test
    
    srcdir = Path(__file__).resolve().parent.parent.parent.parent

    detector, trackingGeometry, decorators = GenericDetector.create()

    field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))

    inputParticlePath = args.input_dir
    if not inputParticlePath.exists():
        inputParticlePath = None

    runCKFTracks(
        trackingGeometry,
        decorators,
        field=field,
        geometrySelection=args.geo_selection_config_file,
        digiConfigFile=args.digi_config_file,
        outputCsv=True,
        truthSmearedSeeded=False,
        truthEstimatedSeeded=False,
        inputParticlePath=inputParticlePath,
        outputDir=outdir,
    ).run()
