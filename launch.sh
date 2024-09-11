#!/bin/sh
docker build -t analyzer .
#docker run -it --rm --name analyzer -v "$PWD":/usr/src/app analyzer python ./inference.py
docker run -it --rm --name analyzer -v "$PWD":/usr/src/app analyzer
