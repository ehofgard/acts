///////////////////////////////////////////////////////////////////
// TrackingVolumeArrayCreator.h, ACTS project
///////////////////////////////////////////////////////////////////

#ifndef ACTS_GEOMETRYTOOLS_TRACKINGVOLUMEARRAYCREATOR_H
#define ACTS_GEOMETRYTOOLS_TRACKINGVOLUMEARRAYCREATOR_H

// Core module
#include "Core/AlgebraDefinitions.h"
// Geometry module
#include "Tools/ITrackingVolumeArrayCreator.h"
#include "GeometryUtils/BinnedArray.h"
// STL
#include <algorithm>

namespace Acts {

    class Layer;
    class TrackingVolume;
    
    typedef std::pair< TrackingVolumePtr, Vector3D>   TrackingVolumeOrderPosition;
    
    
    //typedef std::pair< TrackingVolumePtr, const Transform3D*>  TrackingVolumeNavOrder;


    /** @class TrackingVolumeArrayCreator

      The TrackingVolumeArrayCreator is a simple Tool that helps to construct
      binned arrays of TrackingVolumes for both, confinement in another volume 
      and navigation issues.

      @TODO Julia: make private tools private again after Gaudi update (bug in Gaudi), marked with //b
     
      @author Andreas.Salzburger@cern.ch   
     */

    class TrackingVolumeArrayCreator : public ITrackingVolumeArrayCreator {

      public:
        /** Constructor */
      TrackingVolumeArrayCreator() = default;

      /** Destructor */
      virtual ~TrackingVolumeArrayCreator() = default;

      /** create a tracking volume array */
      std::shared_ptr<const TrackingVolumeArray> trackingVolumeArray(const TrackingVolumeVector& vols, BinningValue bVal) const;  
    };
}

#endif

