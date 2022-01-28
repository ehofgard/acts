// Script for seed finding options

#include "ActsExamples/TrackFinding/SeedFindingOptions.hpp"

#include "Acts/Geometry/GeometryIdentifier.hpp"
#include "ActsExamples/Utilities/Options.hpp"
#include "ActsExamples/EventData/SimSpacePoint.hpp"
#include "Acts/Definitions/Units.hpp"
#include "ActsExamples/Io/Performance/CKFPerformanceWriter.hpp"

#include <string>
#include <iostream>
#include <string>
#include <vector>

// From my understanding, this is doing the boosting?

#include <boost/program_options.hpp>

// Just follow the TrackFindingOptions example because we want to run combinations with a shell script

void ActsExamples::Options::addSeedFindingOptions(
  ActsExamples::Options::Description& desc) {
  using boost::program_options::value;

  auto opt = desc.add_options();

  // Just keep the default values in SeedfinderConfig.hpp
  // This is only if the options are included, then they should
  // be changes in the SeedfinderConfig struct
  // could add value<type>() -> default_value()
  opt("sf-minPt", value<float>(),"Seed finder minimum pT in MeV.");
  opt( "sf-cotThetaMax", value<float>(), "cot of maximum theta angle");
  opt("sf-deltaRMin", value<float>(),
  "Minimum distance in mm between two SPs in a seed");
  opt("sf-deltaRMax", value<float>(),
  "Maximum distance in mm between two SPs in a seed");
  opt("sf-impactMax", value<float>(), "max impact parameter in mm");
  opt("sf-sigmaScattering", value<float>(),
  "How many sigmas of scattering to include in seeds");
  opt("sf-maxSeedsPerSpM", value<size_t>(),
  "How many seeds can share one middle SpacePoint");
  opt("sf-collisionRegionMin", value<float>(),
  "limiting location of collision region in z in mm");
  opt("sf-collisionRegionMax", value<float>(),
  "limiting location of collision region in z in mm");
  opt("sf-zMin", value<float>(),
  "Minimum z of space points included in algorithm");
  opt("sf-zMax", value<float>(),
  "Maximum z of space points included in algorithm");
  opt("sf-rMax", value<float>(),
  "Max radius of Space Points included in algorithm in mm");
  opt("sf-rMin", value<float>(),
  "Min radius of Space Points included in algorithm in mm");
  opt("sf-bFieldInZ", value<float>(), "Magnetic field strength in Tesla");
  //opt("sf-beamPos", value<read_range>()->multitoken()->default_value({0., 0.}),
  //"(x, y) position of the beam to offset Space Points");
  opt("sf-maxPtScattering", value<float>(), "maximum Pt for scattering cut");
  opt("sf-radLengthPerSeed", value<float>(), "Average radiation length");

}

void ActsExamples::Options::addCKFPerfOptions(
  ActsExamples::Options::Description& desc) {
  using boost::program_options::value;
  // Options for optimizing score function based on eta, pt
  // In the future could use this for barrel/endcap dependent scoring
  // Other options to add here?
  auto opt = desc.add_options();
  opt("ckf-EtaMax", value<float>(), "max eta for particles in efficiency calculations");
  opt("ckf-EtaMin", value<float>(), "min eta for particles in efficiency calculations");
  opt("ckf-PtMin", value<float>(), "min transverse momentum for particles in efficiency calculations in GeV");
  opt("ckf-PtMax", value<float>(), "max transverse momentum for particles in efficiency calculations in GeV");
}


void ActsExamples::Options::addMLOutput(
  ActsExamples::Options::Description& desc) {
  using boost::program_options::value;
  auto opt = desc.add_options();
  opt("output-ML", value<bool>(), "true if output should be ML friendly for EA algorithm");
}


bool ActsExamples::Options::readMLOutputConfig(
    const ActsExamples::Options::Variables& vm) {
  bool outputIsML = false;
  if (vm.count("output-ML")) {
    outputIsML = vm["output-ML"].as<bool>();
  }
  return outputIsML;
}

// Read the CKF performance config
ActsExamples::CKFPerformanceWriter::Config ActsExamples::Options::readCKFPerfConfig(
  const ActsExamples::Options::Variables& vm) {
  ActsExamples::CKFPerformanceWriter::Config perfWriterCfg;

  // Need to add these variables to the perfWriterConfig 
  if (vm.count("ckf-EtaMax")) {
    perfWriterCfg.etaMax = vm["ckf-EtaMax"].as<float>();
  }

  if (vm.count("ckf-EtaMin")) {
    perfWriterCfg.etaMin = vm["ckf-EtaMin"].as<float>();
  }

  if (vm.count("ckf-PtMin")) {
    perfWriterCfg.ptMin = vm["ckf-PtMin"].as<float>(); //* Acts::UnitConstants::GeV;
  }

  if (vm.count("ckf-PtMax")) {
    perfWriterCfg.ptMax = vm["ckf-PtMax"].as<float>() * Acts::UnitConstants::GeV;
  }
  // adding ML output option here
  if (vm.count("output-ML")) {
    perfWriterCfg.outputIsML = vm["output-ML"].as<bool>();
  }
  return perfWriterCfg;
  
}

// Add seed finding options here
// Probably better practice to do this here as opposed to in the CKF code 
// return a seedFinderConfig object
Acts::SeedfinderConfig<ActsExamples::SimSpacePoint> ActsExamples::Options::readSeedFindingConfig(
  const ActsExamples::Options::Variables& vm) {
  // Return seedFinderConfig and then set gridFinderConfig variables to be the same in the CKF code
  // Creates a new SeedfinderConfig struct
  Acts::SeedfinderConfig<ActsExamples::SimSpacePoint> cfg;
  //Acts::Seeding::SeedFinderConfig<SpacePoint> cfg;
  // Pretty sure these should just be set up with the default now, if it is supplied in the command line, will be changed from the default
  // compare to variables here https://github.com/ehofgard/acts/blob/main/Core/include/Acts/Seeding/SeedfinderConfig.hpp
  // add more parameters here? 
  if (vm.count("sf-minPt")) {
    cfg.minPt = vm["sf-minPt"].as<float>()*Acts::UnitConstants::MeV;
  }
  if (vm.count("sf-cotThetaMax")) {
    cfg.cotThetaMax = vm["sf-cotThetaMax"].as<float>()*Acts::UnitConstants::mm;;
  }
  if (vm.count("sf-deltaRMin")) {
    cfg.deltaRMin = vm["sf-deltaRMin"].as<float>()*Acts::UnitConstants::mm;;
  }
  if (vm.count("sf-deltaRMax")) {
    cfg.deltaRMax = vm["sf-deltaRMax"].as<float>()*Acts::UnitConstants::mm;
  }
  if (vm.count("sf-impactMax")) {
    cfg.impactMax = vm["sf-impactMax"].as<float>()*Acts::UnitConstants::mm;
  }
  if (vm.count("sf-sigmaScattering")) {
    cfg.sigmaScattering = vm["sf-sigmaScattering"].as<float>();
  }
  if (vm.count("sf-maxSeedsPerSpM")) {
    cfg.maxSeedsPerSpM = vm["sf-maxSeedsPerSpM"].as<size_t>();
  }
  if (vm.count("sf-collisionRegionMin")) {
    cfg.collisionRegionMin = vm["sf-collisionRegionMin"].as<float>()*Acts::UnitConstants::mm;
  }
  if (vm.count("sf-collisionRegionMax")) {
    cfg.collisionRegionMax = vm["sf-collisionRegionMax"].as<float>()*Acts::UnitConstants::mm;
  }
  if (vm.count("sf-zMin")) {
    cfg.zMin = vm["sf-zMin"].as<float>()*Acts::UnitConstants::mm;
  }
  if (vm.count("sf-zMax")) {
    cfg.zMax = vm["sf-zMax"].as<float>()*Acts::UnitConstants::mm;
  }
  if (vm.count("sf-rMax")) {
    cfg.rMax = vm["sf-rMax"].as<float>()*Acts::UnitConstants::mm;
  }
  if (vm.count("sf-rMin")) {
    cfg.rMin = vm["sf-rMin"].as<float>()*Acts::UnitConstants::mm;
  }
  if (vm.count("sf-bFieldInZ")) {
    cfg.bFieldInZ = vm["sf-bFieldInZ"].as<float>()*Acts::UnitConstants::T;
  }
  /*
  if (vm.count("sf-beamPos")) {
    auto beamPos = vm["sf-beamPos"].template as<read_range>();
    if (beamPos.size() != 2) {
      throw std::invalid_argument(
          "Beam position dimension handed over is wrong. It must be of "
          "dimension 2. Beam position specifies the x, y coordinates of the "
          "beam.");
    }
    cfg.beamPos = {beamPos.at(0), beamPos.at(1)};
  }
  */
  if (vm.count("sf-radLengthPerSeed")) {
    cfg.radLengthPerSeed = vm["sf-radLengthPerSeed"].as<float>();
  }
  if (vm.count("sf-maxPtScattering")) {
    cfg.maxPtScattering = vm["sf-maxPtScattering"].as<float>()*Acts::UnitConstants::MeV;
  }
  return cfg;
}
