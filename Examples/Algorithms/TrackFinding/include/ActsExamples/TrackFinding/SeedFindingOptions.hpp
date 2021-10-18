#pragma once

#include "Acts/Utilities/Logger.hpp"
#include "ActsExamples/TrackFinding/SeedingAlgorithm.hpp"
#include "ActsExamples/Utilities/OptionsFwd.hpp"

namespace ActsExamples {
namespace Options {

/// Add TrackFinding options.
///
/// @param desc The options description to add options to for seed finding
void addSeedFindingOptions(Description& desc);

/// Read TrackFinding options to create the algorithm config.
///
/// @param variables The variables to read from for seed finding
SeedFindingAlgorithm::Config readSeedFindingConfig(
    const Variables& variables);

}  // namespace Options
}  // namespace ActsExamples