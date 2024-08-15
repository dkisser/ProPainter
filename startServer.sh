#!/bin/sh

COMMAND="python app.py"

nohup "$COMMAND" >> server.log 2>&1 &