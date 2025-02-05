#!/usr/bin/env python3
import pathlib, acts, acts.examples, itk

u = acts.UnitConstants
geo_dir = pathlib.Path("acts-detector-examples")
outputDir = pathlib.Path.cwd()

detector, trackingGeometry, decorators = itk.buildITkGeometry(geo_dir)
field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

from particle_gun import addParticleGun, MomentumConfig, EtaConfig, ParticleConfig
from fatras import addFatras
from digitization import addDigitization
from seeding import addSeeding, SeedingAlgorithm, TruthSeedRanges
from ckf_tracks import addCKFTracks

s = acts.examples.Sequencer(events=100, numThreads=-1)
s = addParticleGun(
    s,
    MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, True),
    EtaConfig(-4.0, 4.0, True),
    ParticleConfig(1, acts.PdgParticle.eMuon, True),
    rnd=rnd,
)
s = addFatras(
    s,
    trackingGeometry,
    field,
    outputDirRoot=outputDir,
    rnd=rnd,
)
s = addDigitization(
    s,
    trackingGeometry,
    field,
    digiConfigFile=geo_dir / "atlas/itk-hgtd/itk-smearing-config.json",
    outputDirRoot=outputDir,
    rnd=rnd,
)
s = addSeeding(
    s,
    trackingGeometry,
    field,
    TruthSeedRanges(pt=(1.0 * u.GeV, None), eta=(-4.0, 4.0), nHits=(9, None)),
    geoSelectionConfigFile=geo_dir / "atlas/itk-hgtd/geoSelection-ITk.json",
    outputDirRoot=outputDir,
)
s = addCKFTracks(
    s,
    trackingGeometry,
    field,
    TruthSeedRanges(pt=(400.0 * u.MeV, None), nHits=(6, None)),
    outputDirRoot=outputDir,
)

s.run()
