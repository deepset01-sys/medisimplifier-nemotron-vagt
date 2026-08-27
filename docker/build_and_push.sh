#!/bin/bash
set -e
GIT_SHA=$(git rev-parse HEAD)
docker build --build-arg GIT_SHA=$GIT_SHA \
             -t chambul/medisimplifier:train-v28 \
             -f docker/Dockerfile.train .
docker push chambul/medisimplifier:train-v28
echo "Done: chambul/medisimplifier:train-v28"
