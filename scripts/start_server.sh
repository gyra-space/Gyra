#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/packages/gyra-app/src:$(pwd)/packages/gyra-core/src:$(pwd)/packages/gyra-serve/src:$(pwd)/packages/gyra-ext/src:$(pwd)/packages/gyra-client/src
echo "Starting server with PYTHONPATH=$PYTHONPATH"
nohup .venv/bin/python packages/gyra-app/src/gyra_app/gyra_server.py --config configs/my/dev-1.toml > server.log 2>&1 &
echo "Server started with PID $!"
