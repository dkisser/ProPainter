#!/bin/sh

COMMAND="celery -A celery_app worker --loglevel=info -c 1"

nohup $COMMAND >> worker.log 2>&1 &