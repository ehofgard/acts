// This file is part of the Acts project.
//
// Copyright (C) 2019 CERN for the benefit of the Acts project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at http://mozilla.org/MPL/2.0/.

#include <algorithm>
#include "Acts/Vertexing/VertexingError.hpp"

template <typename input_track_t>
Acts::Result<void> Acts::KalmanVertexUpdater::updateVertexWithTrack(
    Vertex<input_track_t>* vtx, TrackAtVertex<input_track_t>& trk) {
  if (vtx == nullptr) {
    return VertexingError::EmptyInput;
  }

  auto res = detail::update<input_track_t>(vtx, trk, 1);

  if (!res.ok()) {
    return res.error();
  }

  return {};
}

template <typename input_track_t>
Acts::Result<Acts::Vertex<input_track_t>>
Acts::KalmanVertexUpdater::updatePosition(
    const Acts::Vertex<input_track_t>* vtx,
    const Acts::LinearizedTrack& linTrack, double trackWeight, int sign) {
  if (vtx == nullptr) {
    return VertexingError::EmptyInput;
  }

  // Retrieve linTrack information
  const SpacePointToBoundMatrix& posJac = linTrack.positionJacobian;
  const ActsMatrixD<BoundParsDim, 3>& momJac =
      linTrack.momentumJacobian;  // B_k in comments below
  const BoundVector& trkParams = linTrack.parametersAtPCA;
  const BoundVector& constTerm = linTrack.constantTerm;
  const BoundSymMatrix& trkParamWeight =
      linTrack.covarianceAtPCA.inverse();  // G_k in comments below

  // Vertex to be updated
  const SpacePointVector& oldVtxPos = vtx->fullPosition();
  const SpacePointSymMatrix& oldVtxWeight = vtx->fullCovariance().inverse();

  // W_k matrix
  ActsSymMatrixD<3> wMat =
      (momJac.transpose() * (trkParamWeight * momJac)).inverse();

  // G_b = G_k - G_k*B_k*W_k*B_k^(T)*G_k^T
  BoundSymMatrix gBmat =
      trkParamWeight - trkParamWeight * (momJac * (wMat * momJac.transpose())) *
                           trkParamWeight.transpose();

  // New vertex cov matrix
  SpacePointSymMatrix newVtxCov =
      (oldVtxWeight +
       trackWeight * sign * posJac.transpose() * (gBmat * posJac))
          .inverse();

  // New vertex position
  SpacePointVector newVtxPos =
      newVtxCov *
      (oldVtxWeight * oldVtxPos + trackWeight * sign * posJac.transpose() *
                                      gBmat * (trkParams - constTerm));

  // Create return vertex with new position
  // and covariance, but w/o tracks
  Vertex<input_track_t> returnVertex;

  // Set position
  returnVertex.setFullPosition(newVtxPos);
  // Set cov
  returnVertex.setFullCovariance(newVtxCov);
  // Set fit quality
  returnVertex.setFitQuality(vtx->fitQuality().first, vtx->fitQuality().second);

  return returnVertex;
}

template <typename input_track_t>
double Acts::KalmanVertexUpdater::detail::vertexPositionChi2(
    const Vertex<input_track_t>* oldVtx, const Vertex<input_track_t>* newVtx) {
  SpacePointSymMatrix oldWeight = oldVtx->fullCovariance().inverse();
  SpacePointVector posDiff = newVtx->fullPosition() - oldVtx->fullPosition();

  // Calculate and return corresponding chi2
  return posDiff.transpose() * (oldWeight * posDiff);
}

template <typename input_track_t>
double Acts::KalmanVertexUpdater::detail::trackParametersChi2(
    const Vertex<input_track_t>& vtx, const LinearizedTrack& linTrack) {
  const SpacePointVector& vtxPos = vtx.fullPosition();

  // Track properties
  const SpacePointToBoundMatrix& posJac = linTrack.positionJacobian;
  const ActsMatrixD<BoundParsDim, 3>& momJac = linTrack.momentumJacobian;
  const BoundVector& trkParams = linTrack.parametersAtPCA;
  const BoundVector& constTerm = linTrack.constantTerm;
  const BoundSymMatrix& trkParamWeight = linTrack.covarianceAtPCA.inverse();

  // Calculate temp matrix S
  ActsSymMatrixD<3> matS =
      (momJac.transpose() * (trkParamWeight * momJac)).inverse();

  // Refitted track momentum
  Vector3D newTrackMomentum = matS * momJac.transpose() * trkParamWeight *
                              (trkParams - constTerm - posJac * vtxPos);

  // Refitted track parameters
  auto newTrkParams = constTerm + posJac * vtxPos + momJac * newTrackMomentum;

  // Parameter difference
  auto paramDiff = trkParams - newTrkParams;

  // Return chi2
  return paramDiff.transpose() * (trkParamWeight * paramDiff);
}

template <typename input_track_t>
Acts::Result<void> Acts::KalmanVertexUpdater::detail::update(
    Vertex<input_track_t>* vtx, TrackAtVertex<input_track_t>& trk, int sign) {
  double trackWeight = trk.trackWeight;

  auto res = updatePosition(vtx, trk.linearizedState, trackWeight, sign);

  if (!res.ok()) {
    return res.error();
  }

  Vertex<input_track_t> tempVtx = *res;

  // Get fit quality parameters wrt to old vertex
  std::pair fitQuality = vtx->fitQuality();
  double chi2 = fitQuality.first;
  double ndf = fitQuality.second;

  // Chi2 wrt to track parameters
  double trkChi2 =
      detail::trackParametersChi2<input_track_t>(tempVtx, trk.linearizedState);

  // Calculate new chi2
  chi2 += sign * (detail::vertexPositionChi2<input_track_t>(vtx, &tempVtx) +
                  trackWeight * trkChi2);

  // Calculate ndf
  ndf += sign * trackWeight * 2.;

  // Updating the vertex
  vtx->setFullPosition(tempVtx.fullPosition());
  vtx->setFullCovariance(tempVtx.fullCovariance());
  vtx->setFitQuality(chi2, ndf);

  // Updates track at vertex if already there
  // by removing it first and adding new one.
  // Otherwise just adds track to existing list of tracks at vertex
  if (sign > 0) {
    // Remove old track if already there
    detail::removeTrackIf<input_track_t>(vtx, trk);
    // Add track with updated ndf
    auto tracksAtVertex = vtx->tracks();
    // Update track and add to list
    trk.chi2Track = trkChi2;
    trk.ndf = 2 * trackWeight;
    tracksAtVertex.push_back(trk);
    vtx->setTracksAtVertex(tracksAtVertex);
  }
  // Remove trk from current vertex
  if (sign < 0) {
    detail::removeTrackIf<input_track_t>(vtx, trk);
  }

  return {};
}

template <typename input_track_t>
void Acts::KalmanVertexUpdater::detail::removeTrackIf(
    Vertex<input_track_t>* vtx, const TrackAtVertex<input_track_t>& trk) {
  auto tracksAtVertex = vtx->tracks();
  auto removeIter = std::find_if(tracksAtVertex.begin(), tracksAtVertex.end(),
                                 [&trk](const auto& trkAtVertex) {
                                   return trk.fittedParams.parameters() ==
                                          trkAtVertex.fittedParams.parameters();
                                 });
  if (removeIter != tracksAtVertex.end()) {
    tracksAtVertex.erase(removeIter);
  }
  vtx->setTracksAtVertex(tracksAtVertex);
}