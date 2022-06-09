#!/usr/bin/env python3

import argparse
from pathlib import Path
from typing import Optional
import acts, acts.examples, itk

from particle_gun import addParticleGun, MomentumConfig, EtaConfig, ParticleConfig
from fatras import addFatras
from digitization import addDigitization
from seeding import addSeeding, SeedingAlgorithm, TruthSeedRanges,SeedfinderConfigArg,ParticleSmearingSigmas
from ckf_tracks import addCKFTracks
from acts import UnitConstants as u
from acts.examples import Sequencer, GenericDetector, RootParticleReader



if "__main__" == __name__:
    # Insert argument parser dudes
    # defaults are in ckf_tracks.py
    p = argparse.ArgumentParser(
        description = "Example script to run the generic detector with parameter changes",
    )
    p.add_argument(
        "--sf_minPt",
        default = 900.0,
        type = float,
        help = "Seed finder minimum pT in MeV."
    )

    # need to rerun optuna with higher cotThetaMax
    p.add_argument(
        "--sf_cotThetaMax",
        default = 7.40627,
        type = float,
        help = "cot of maximum theta angle"
    )

    p.add_argument(
        "--sf_deltaRMin",
        default = 20.0,
        type = float,
        help = "Minimum distance in mm between two SPs in a seed"
    )

    p.add_argument(
        "--sf_deltaRMax",
        default = 280.0,
        type = float,
        help = "Maximum distance in mm between two SPs in a seed"
    )

    p.add_argument(
        "--sf_impactMax",
        default = 2.0,
        type = float,
        help = "max impact parameter in mm"
    )

    p.add_argument(
        "--sf_sigmaScattering",
        default = 2,
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
        default = -200.0,
        type = float,
        help = "limiting location of collision region in z in mm"
    )

    p.add_argument(
        "--sf_collisionRegionMax",
        default = 200.0,
        type = float,
        help = "limiting location of collision region in z in mm"
    )

    p.add_argument(
        "--sf_zMin",
        default = -3000.0,
        type = float,
        help = "Minimum z of space points included in algorithm"
    )

    p.add_argument(
        "--sf_zMax",
        default = 3000.0,
        type = float,
        help = "Maximum z of space points included in algorithm"
    )

    p.add_argument(
        "--sf_rMax",
        default = 320.0,
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
        default = 10000,
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
    # idk where these are in the python scripts? 
    
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

    p.add_argument(
        "--default_arg",
        default = False,
        action = 'store_true',
        help = "Use default arguments in the CKF"
    )

    # Make output directory
    args = p.parse_args()
    outdir = args.output_dir
    args.output_dir.mkdir(exist_ok=True, parents=True)
    
    srcdir = Path(__file__).resolve().parent.parent.parent.parent

    #geo_dir = Path("/afs/cern.ch/work/e/ehofgard/acts-detector-examples/acts-detector-examples")
    #detector, trackingGeometry, decorators = itk.buildITkGeometry(geo_dir)

    detector, trackingGeometry, decorators = GenericDetector.create()

    field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))
    rnd = acts.examples.RandomNumbers(seed=42)

    inputParticlePath = args.input_dir
    if not inputParticlePath.exists():
        inputParticlePath = None

    s = acts.examples.Sequencer(events=100, numThreads=-1)
    logger = acts.logging.getLogger("CKFExample")

    default_arg = args.default_arg

    if inputParticlePath is None:
        logger.info("Generating particles using particle gun")
        s = addParticleGun(
        s,
        MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, True),
        EtaConfig(-4.0, 4.0, True),
        ParticleConfig(1, acts.PdgParticle.eMuon, True),
        rnd=rnd,
    )

    else:
        logger.info("Reading particles from %s", inputParticlePath.resolve())
        assert inputParticlePath.exists()
        #inputParticles = "particles_read"
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
        outputDirRoot=outdir,
        rnd=rnd,
        outputIsML = args.outputIsML,
    )

    s = addDigitization(
        s,
        trackingGeometry,
        field,
        #digiConfigFile=geo_dir / "atlas/itk-hgtd/itk-smearing-config.json",
        digiConfigFile = Path("/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/Digitization/share/default-smearing-config-generic.json"),
        outputDirRoot=outdir,
        rnd=rnd,
    )

    s = addSeeding(
        s,
        trackingGeometry,
        field,
        #TruthSeedRanges(pt=(1.0 * u.GeV, None), eta=(-4.0, 4.0), nHits=(9, None)),
        # THESE WERE THE PARAMETERS USED FOR GENERIC DETECTOR
        # TruthSeedRanges(pt=(1.0 * u.GeV, None), eta=(-3.0, 3.0), nHits=(6, None)),
        # eta 1.5 for barrel
        TruthSeedRanges(pt=(1.0 * u.GeV, None), eta=(-3.0, 3.0), nHits=(6, None)), 
        SeedfinderConfigArg(
            r = (args.sf_rMin*u.mm,args.sf_rMax*u.mm),
            deltaR = (args.sf_deltaRMin*u.mm,args.sf_deltaRMax*u.mm),
            collisionRegion = (args.sf_collisionRegionMin*u.mm,args.sf_collisionRegionMax*u.mm),
            z = (args.sf_zMin*u.mm,args.sf_zMax*u.mm),
            maxSeedsPerSpM = args.sf_maxSeedsPerSpM,
            sigmaScattering = args.sf_sigmaScattering,
            radLengthPerSeed = args.sf_radLengthPerSeed,
            minPt = args.sf_minPt*u.MeV,
            bFieldInZ = 1.99724 * u.T,
            impactMax = args.sf_impactMax*u.mm,
            cotThetaMax = args.sf_cotThetaMax,
            maxPtScattering = args.sf_maxPtScattering,
        ),
        geoSelectionConfigFile="/afs/cern.ch/work/e/ehofgard/acts/Examples/Algorithms/TrackFinding/share/geoSelection-genericDetector.json",
        #geoSelectionConfigFile=geo_dir / "atlas/itk-hgtd/geoSelection-ITk.json",
        outputDirRoot=outdir,
    )
    '''
    else:
        s = addSeeding(
            s,
            trackingGeometry,
            field,
            TruthSeedRanges(pt=(1.0 * u.GeV, None), eta=(-4.0, 4.0), nHits=(9, None)),
            SeedfinderConfigArg(),
            geoSelectionConfigFile=geo_dir / "atlas/itk-hgtd/geoSelection-ITk.json",
            outputDirRoot=outdir,
        )
    '''

    # Note this should be changed in future iterations
    # Should be changed to match truth seed ranges above
    s = addCKFTracks(
        s,
        trackingGeometry,
        field,
        TruthSeedRanges(pt=(1.0 * u.GeV, None), nHits=(6, None)),
        outputDirRoot=outdir,
        outputIsML = args.outputIsML,
    )

    s.run()
