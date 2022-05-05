#!/bin/bash

isITk=true

nEvt=1
npileup=140

#./runVertexing.sh --tracksMaxZinterval=3.0 --tracksMaxSignificance=5.0 --maxVertexChi2=18.42 --maxMergeVertexSignificance=3.0 --minWeight=0.0001 --maxIterations=100 --maximumVertexContamination=0.5

OptDir=/afs/cern.ch/work/r/rgarg/public/ACTS-Project/ParameterOptimization/

InputDir=${OptDir}/TrainData/gen/ttbarPythia_mu${npileup}_n${nEvt}/

if ${isITk}
then
    InTrackDir=${OptDir}/TrainData/tracks_itk/CKF_mu${npileup}_n${nEvt}/
    outputDir=${OptDir}/TrainData/vertex_itk/AMVF_mu${npileup}_n${nEvt}/
else
    InTrackDir=${OptDir}/TrainData/tracks/CKF_mu${npileup}_n${nEvt}/
    outputDir=${OptDir}/TrainData/vertex/AMVF_mu${npileup}_n${nEvt}/
fi

echo "InTrack Dir: ${InTrackDir}"
echo "Output Dir: ${outputDir}"

if [ -d ${outputDir} ]
then
    echo "Output Directory already exists"
else
    echo "Making Output Directory:: ${outputDir}" 
    
    mkdir -p ${outputDir}
fi

#python vertex_fitting.py --indir=${InputDir} --intracksdir=${InTrackDir} --output=${outputDir} --nEvents=${nEvt} --tracksMaxZinterval=${TracksMaxZint} --tracksMaxSignificance=${TracksMaxSig} --maxVertexChi2=${MaxVtxChi2} --maxMergeVertexSignificance=${MaxMergeVtxSig} --minWeight=${MinWt} --maxIterations=${MaxItr} --maximumVertexContamination=${MaxVtxCont}
if ${isITk}
then
    python vertex_fitting_itk.py --indir=${InputDir} --intracksdir=${InTrackDir} --output=${outputDir} --nEvents=${nEvt} $1 $2 $3 $4 $5 $6 $7
else
    python vertex_fitting.py --indir=${InputDir} --intracksdir=${InTrackDir} --output=${outputDir} --nEvents=${nEvt} $1 $2 $3 $4 $5 $6 $7
fi
