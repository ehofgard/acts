// This file is part of the Acts project.
//
// Copyright (C) 2019 CERN for the benefit of the Acts project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at http://mozilla.org/MPL/2.0/.

// clang-format off
#define BOOST_TEST_MODULE ZScanVertexFinder Tests
#define BOOST_TEST_DYN_LINK
#include <boost/test/unit_test.hpp>
#include <boost/test/data/test_case.hpp>
#include <boost/test/output_test_stream.hpp>
// clang-format on

#include "Acts/EventData/TrackParameters.hpp"
#include "Acts/MagneticField/ConstantBField.hpp"
#include "Acts/Surfaces/PerigeeSurface.hpp"
#include "Acts/Tests/CommonHelpers/FloatComparisons.hpp"
#include "Acts/Utilities/Definitions.hpp"
#include "Acts/Utilities/Units.hpp"

#include "Acts/Propagator/Propagator.hpp"
#include "Acts/Propagator/EigenStepper.hpp"

#include "Acts/Vertexing/ZScanVertexFinder.hpp"
#include "Acts/Vertexing/FsmwMode1dFinder.hpp"
#include "Acts/Vertexing/TrackToVertexIPEstimator.hpp"

namespace bdata = boost::unit_test::data;

namespace Acts {
namespace Test {

using Covariance = BoundSymMatrix;

// Create a test context
GeometryContext tgContext = GeometryContext();
MagneticFieldContext mfContext = MagneticFieldContext();

// Vertex x/y position distribution
std::uniform_real_distribution<> vXYDist(-0.1 * units::_mm, 0.1 * units::_mm);
// Vertex z position distribution
std::uniform_real_distribution<> vZDist(-20 * units::_mm, 20 * units::_mm);
// Track d0 distribution
std::uniform_real_distribution<> d0Dist(-0.01 * units::_mm, 0.01 * units::_mm);
// Track z0 distribution
std::uniform_real_distribution<> z0Dist(-0.2 * units::_mm, 0.2 * units::_mm);
// Track pT distribution
std::uniform_real_distribution<> pTDist(0.4 * units::_GeV, 10. * units::_GeV);
// Track phi distribution
std::uniform_real_distribution<> phiDist(-M_PI, M_PI);
// Track theta distribution
std::uniform_real_distribution<> thetaDist(1.0, M_PI - 1.0);
// Track charge helper distribution
std::uniform_real_distribution<> qDist(-1, 1);
// Track IP resolution distribution
std::uniform_real_distribution<> resIPDist(0., 100. * units::_um);
// Track angular distribution
std::uniform_real_distribution<> resAngDist(0., 0.1);
// Track q/p resolution distribution
std::uniform_real_distribution<> resQoPDist(-0.01, 0.01);

///
/// @brief Unit test for ZScanVertexFinder
///
BOOST_AUTO_TEST_CASE(zscan_finder_test) {
  unsigned int nTests = 50;

  for (unsigned int iTest = 0; iTest < nTests; ++iTest) {
    // Number of tracks
    unsigned int nTracks = 30;

    // Set up RNG
    int mySeed = 31415;
    std::mt19937 gen(mySeed);

    // Set up constant B-Field
    ConstantBField bField(Vector3D(0., 0., 1.) * units::_T);

    // Set up Eigenstepper
    EigenStepper<ConstantBField> stepper(bField);

    // Set up propagator with void navigator
    Propagator<EigenStepper<ConstantBField>> propagator(stepper);

    // Create perigee surface
    std::shared_ptr<PerigeeSurface> perigeeSurface =
        Surface::makeShared<PerigeeSurface>(Vector3D(0., 0., 0.));

    // Create position of vertex and perigee surface
    double x = vXYDist(gen);
    double y = vXYDist(gen);
    double z = vZDist(gen);

    // Calculate d0 and z0 corresponding to vertex position
    double d0_v = sqrt(x * x + y * y);
    double z0_v = z;

    // Start constructing nTracks tracks in the following
    std::vector<BoundParameters> tracks;

    // Construct random track emerging from vicinity of vertex position
    // Vector to store track objects used for vertex fit
    for (unsigned int iTrack = 0; iTrack < nTracks; iTrack++) {
      // Construct positive or negative charge randomly
      double q = qDist(gen) < 0 ? -1. : 1.;

      // Construct random track parameters
      TrackParametersBase::ParVector_t paramVec;
      double z0track = z0_v + z0Dist(gen);
      paramVec << d0_v + d0Dist(gen), z0track, phiDist(gen), thetaDist(gen),
          q / pTDist(gen), 0.;

      // Fill vector of track objects with simple covariance matrix
      std::unique_ptr<Covariance> covMat = std::make_unique<Covariance>();

      // Resolutions
      double resD0 = resIPDist(gen);
      double resZ0 = resIPDist(gen);
      double resPh = resAngDist(gen);
      double resTh = resAngDist(gen);
      double resQp = resQoPDist(gen);

      (*covMat) << resD0 * resD0, 0., 0., 0., 0., 0., 0., resZ0 * resZ0, 0., 0.,
          0., 0., 0., 0., resPh * resPh, 0., 0., 0., 0., 0., 0., resTh * resTh,
          0., 0., 0., 0., 0., 0., resQp * resQp, 0., 0., 0., 0., 0., 0., 1.;
      tracks.push_back(BoundParameters(tgContext, std::move(covMat), paramVec,
                                       perigeeSurface));
    }

    ZScanVertexFinder<ConstantBField, BoundParameters,
                      Propagator<EigenStepper<ConstantBField>>>::Config cfg;
    ZScanVertexFinder<ConstantBField, BoundParameters,
                      Propagator<EigenStepper<ConstantBField>>>::State state;

    ZScanVertexFinder<ConstantBField, BoundParameters,
                      Propagator<EigenStepper<ConstantBField>>>
        finder(std::move(cfg));

    VertexFinderOptions<BoundParameters> vFinderOptions(tgContext, mfContext);

    auto res = finder.find(tracks, state, propagator, vFinderOptions);

    BOOST_CHECK(res.ok());

    if (res.ok()) {
      Vector3D result = state.vertexCollection[0].position();
      CHECK_CLOSE_ABS(result[eZ], z, 1 * units::_mm);
    }
  }
}

// Dummy user-defined InputTrack type
struct InputTrack {
  InputTrack(const BoundParameters& params) : m_parameters(params) {}

  const BoundParameters& parameters() const { return m_parameters; }

  // store e.g. link to original objects here

 private:
  BoundParameters m_parameters;
};

///
/// @brief Unit test for ZScanVertexFinder with user-defined input track type
///
BOOST_AUTO_TEST_CASE(zscan_finder_usertrack_test) {
  unsigned int nTests = 50;

  for (unsigned int iTest = 0; iTest < nTests; ++iTest) {
    // Number of tracks
    unsigned int nTracks = 30;

    // Set up RNG
    int mySeed = 31415;
    std::mt19937 gen(mySeed);

    // Set up constant B-Field
    ConstantBField bField(Vector3D(0., 0., 1.) * units::_T);

    // Set up Eigenstepper
    EigenStepper<ConstantBField> stepper(bField);

    // Set up propagator with void navigator
    Propagator<EigenStepper<ConstantBField>> propagator(stepper);

    // Create perigee surface
    std::shared_ptr<PerigeeSurface> perigeeSurface =
        Surface::makeShared<PerigeeSurface>(Vector3D(0., 0., 0.));

    // Create position of vertex and perigee surface
    double x = vXYDist(gen);
    double y = vXYDist(gen);
    double z = vZDist(gen);

    // Calculate d0 and z0 corresponding to vertex position
    double d0_v = sqrt(x * x + y * y);
    double z0_v = z;

    // Start constructing nTracks tracks in the following
    std::vector<InputTrack> tracks;

    // Construct random track emerging from vicinity of vertex position
    // Vector to store track objects used for vertex fit
    for (unsigned int iTrack = 0; iTrack < nTracks; iTrack++) {
      // Construct positive or negative charge randomly
      double q = qDist(gen) < 0 ? -1. : 1.;

      // Construct random track parameters
      TrackParametersBase::ParVector_t paramVec;
      double z0track = z0_v + z0Dist(gen);
      paramVec << d0_v + d0Dist(gen), z0track, phiDist(gen), thetaDist(gen),
          q / pTDist(gen), 0.;

      // Fill vector of track objects with simple covariance matrix
      std::unique_ptr<Covariance> covMat = std::make_unique<Covariance>();

      // Resolutions
      double resD0 = resIPDist(gen);
      double resZ0 = resIPDist(gen);
      double resPh = resAngDist(gen);
      double resTh = resAngDist(gen);
      double resQp = resQoPDist(gen);

      (*covMat) << resD0 * resD0, 0., 0., 0., 0., 0., 0., resZ0 * resZ0, 0., 0.,
          0., 0., 0., 0., resPh * resPh, 0., 0., 0., 0., 0., 0., resTh * resTh,
          0., 0., 0., 0., 0., 0., resQp * resQp, 0., 0., 0., 0., 0., 0., 1.;
      tracks.push_back(InputTrack(BoundParameters(tgContext, std::move(covMat),
                                                  paramVec, perigeeSurface)));
    }

    ZScanVertexFinder<ConstantBField, InputTrack,
                      Propagator<EigenStepper<ConstantBField>>>::Config cfg;
    ZScanVertexFinder<ConstantBField, InputTrack,
                      Propagator<EigenStepper<ConstantBField>>>::State state;

    // Create a custom std::function to extract BoundParameters from
    // user-defined InputTrack
    std::function<BoundParameters(InputTrack)> extractParameters =
        [](InputTrack params) { return params.parameters(); };

    ZScanVertexFinder<ConstantBField, InputTrack,
                      Propagator<EigenStepper<ConstantBField>>>
        finder(std::move(cfg), extractParameters);

    VertexFinderOptions<InputTrack> vFinderOptions(tgContext, mfContext);

    auto res = finder.find(tracks, state, propagator, vFinderOptions);

    BOOST_CHECK(res.ok());

    if (res.ok()) {
      Vector3D result = state.vertexCollection[0].position();
      CHECK_CLOSE_ABS(result[eZ], z, 1 * units::_mm);
    }
  }
}

}  // namespace Test
}  // namespace Acts