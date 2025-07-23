#!/bin/bash

# runs grid test with data loader
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)
LIB_DIR=$(realpath "${SCRIPT_DIR}/../lib" )

# check if virtualenv is enabled
[[ ! -z "$VIRTUAL_ENV" ]] || (echo "[ERROR]  Activate virtualenv!" ; exit 1 )

echo "[INFO]  Running test: python ${SCRIPT_DIR}/parallel-audio-loader.py"
PYTHONPATH=$LIB_DIR python ${SCRIPT_DIR}/parallel-audio-loader.py  

echo "[INFO]  Done"
