#!/bin/zsh
cd "$(dirname "$0")"
python3 server.py &
SERVER_PID=$!
sleep 1
open "http://127.0.0.1:43128/"
wait $SERVER_PID
