#!/usr/bin/env python3
#### NEED TO MERGE THIS WITH NEW CHANGES ####
from pathlib import Path
from typing import Optional

from acts.examples import Sequencer, GenericDetector, RootParticleReader

import acts
import itk

from acts import UnitConstants as u
import argparse


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

    s = s or Sequencer(events=100, numThreads=-1)

    logger = acts.logging.getLogger("CKFExample")

    for d in decorators:
        s.addContextDecorator(d)

    rnd = acts.examples.RandomNumbers(seed=42)

    if inputParticlePath is None:
        logger.info("Generating particles using particle gun")

        evGen = acts.examples.EventGenerator(
            level=acts.logging.INFO,
            generators=[
                acts.examples.EventGenerator.Generator(
                    multiplicity=acts.examples.FixedMultiplicityGenerator(n=1),
                    vertex=acts.examples.GaussianVertexGenerator(
                        stddev=acts.Vector4(0, 0, 0, 0), mean=acts.Vector4(0, 0, 0, 0)
                    ),
                    particles=acts.examples.ParametricParticleGenerator(
                        p=(1 * u.GeV, 10 * u.GeV),
                        pTransverse = True,
                        eta=(-4, 4),
                        etaUniform = True,
                        #phi=(0, 360 * u.degree),
                        randomizeCharge=True,
                        numParticles=1,
                        pdg = acts.PdgParticle.eMuon,
                    ),
                )
            ],
            outputParticles="particles_input",
            randomNumbers=rnd,
        )
        s.addReader(evGen)
        inputParticles = evGen.config.outputParticles
    else:
        logger.info("Reading particles from %s", inputParticlePath.resolve())
        assert inputParticlePath.exists()
        inputParticles = "particles_read"
        s.addReader(
            RootParticleReader(
                level=acts.logging.INFO,
                filePath=str(inputParticlePath.resolve()),
                particleCollection=inputParticles,
                orderedEvents=False,
            )
        )

    # Selector
    # Try commenting this out
    preselectParticles = True
    if preselectParticles:
        particles_selected = "particles_selected"
        selector = acts.examples.ParticleSelector(
            level=acts.logging.INFO,
            inputParticles=inputParticles,
            outputParticles=particles_selected,
            absEtaMax = 4.0,
            ptMin = 1*u.GeV,
        )
        s.addAlgorithm(selector)
    else:
        particles_selected = inputParticles

    # Simulation
    simAlg = acts.examples.FatrasSimulation(
        level=acts.logging.INFO,
        inputParticles=particles_selected,
        outputParticlesInitial="particles_initial",
        outputParticlesFinal="particles_final",
        outputSimHits="simhits",
        randomNumbers=rnd,
        trackingGeometry=trackingGeometry,
        magneticField=field,
        generateHitsOnSensitive=True,
    )
    s.addAlgorithm(simAlg)

    # Run the sim hits smearing
    digiCfg = acts.examples.DigitizationConfig(
        acts.examples.readDigiConfigFromJson(str(digiConfigFile)),
        trackingGeometry=trackingGeometry,
        randomNumbers=rnd,
        inputSimHits=simAlg.config.outputSimHits,
    )
    digiAlg = acts.examples.DigitizationAlgorithm(digiCfg, acts.logging.INFO)
    s.addAlgorithm(digiAlg)

    # Run the particle selection
    # The pre-selection will select truth particles satisfying provided criteria
    # from all particles read in by particle reader for further processing. It
    # has no impact on the truth hits themselves
    selAlg = acts.examples.TruthSeedSelector(
        level=acts.logging.INFO,
        # ItK detector
        ptMin=1 * u.GeV,
        # change to 6
        nHitsMin=9,
        absEtaMax = 4.0,
        inputParticles=simAlg.config.outputParticlesInitial,
        inputMeasurementParticlesMap=digiCfg.outputMeasurementParticlesMap,
        outputParticles="particles_seed_selected",
    )
    s.addAlgorithm(selAlg)

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
        if args.outputIsML == False:
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
        ),
    )
    s.addAlgorithm(trackFinder)

    # write track states from CKF
    if args.outputIsML == False:
        trackStatesWriter = acts.examples.RootTrajectoryStatesWriter(
            level=acts.logging.INFO,
            inputTrajectories=trackFinder.config.outputTrajectories,
            # @note The full particles collection is used here to avoid lots of warnings
            # since the unselected CKF track might have a majority particle not in the
            # filtered particle collection. This could be avoided when a seperate track
            # selection algorithm is used.
            inputParticles=particles_selected,
            inputSimHits=simAlg.config.outputSimHits,
            inputMeasurementParticlesMap=digiAlg.config.outputMeasurementParticlesMap,
            inputMeasurementSimHitsMap=digiAlg.config.outputMeasurementSimHitsMap,
            filePath=str(outputDir / "trackstates_ckf.root"),
            treeName="trackstates",
        )
        s.addWriter(trackStatesWriter)

    # write track summary from CKF
    if args.outputIsML == False:
        trackSummaryWriter = acts.examples.RootTrajectorySummaryWriter(
            level=acts.logging.INFO,
            inputTrajectories=trackFinder.config.outputTrajectories,
            # @note The full particles collection is used here to avoid lots of warnings
            # since the unselected CKF track might have a majority particle not in the
            # filtered particle collection. This could be avoided when a seperate track
            # selection algorithm is used.
            inputParticles=particles_selected,
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

    return s


if "__main__" == __name__:
    # Insert argument parser dudes
    # defaults are in ckf_tracks.py
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
        default = 60,
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
        default = 50,
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
        default = None,
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

    # parser.add_argument('-b', action='store_true', default=False)
    p.add_argument(
        "--outputIsML",
        default = False,
        action='store_true',
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

    geo_dir = Path("/afs/cern.ch/work/e/ehofgard/acts-detector-examples/acts-detector-examples")
    detector, trackingGeometry, decorators = itk.buildITkGeometry(geo_dir)

    #detector, trackingGeometry, decorators = GenericDetector.create()

    field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))

    inputParticlePath = args.input_dir
    if not inputParticlePath.exists():
        inputParticlePath = None

    runCKFTracks(
        trackingGeometry,
        decorators,
        field=field,
        geometrySelection=geo_dir / "atlas/itk-hgtd/geoSelection-ITk.json",
        digiConfigFile=geo_dir / "atlas/itk-hgtd/itk-smearing-config.json",
        outputCsv=False,
        truthSmearedSeeded=False,
        truthEstimatedSeeded=False,
        inputParticlePath=inputParticlePath,
        outputDir=outdir,
    ).run()
