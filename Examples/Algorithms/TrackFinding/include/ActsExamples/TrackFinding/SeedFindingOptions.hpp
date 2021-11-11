#pragma once

#include "Acts/Utilities/Logger.hpp"
#include "ActsExamples/TrackFinding/SeedingAlgorithm.hpp"
#include "ActsExamples/Utilities/OptionsFwd.hpp"
#include "ActsExamples/EventData/SimSpacePoint.hpp"
#include "ActsExamples/Io/Performance/CKFPerformanceWriter.hpp"

namespace ActsExamples {
namespace Options {

/// Add TrackFinding options.
///
/// @param desc The options description to add options to for seed finding
void addSeedFindingOptions(Description& desc);

/// ToDo: Add TrackPerformanceOptions
// Not sure if this is the best place to put this

// Options to filter particles when analyzing performance
void addCKFPerfOptions(Description& desc);

// Options for ML friendly output for EA algorithm
void addMLOutput(Description& desc);
/// Read SeedFinding options to create the algorithm config.
///
/// @param variables The variables to read from for seed finding
/// Note this will take in the variable map
Acts::SeedfinderConfig<ActsExamples::SimSpacePoint> readSeedFindingConfig(
    const Variables& variables);

bool readMLOutputConfig(const Variables& variables);

ActsExamples::CKFPerformanceWriter::Config readCKFPerfConfig(
    const Variables& variables);
}  // namespace Options
} // namespace ActsExamples
// Just incorporating outputML in CKF performance writer config
/*\
bool readMLOutputConfig(const Variables& variables);
}
}  // namespace ActsExamples
*/
