#!/bin/sh
exec gunicorn -k uvicorn.workers.UvicornWorker -c uvicorn_conf.py  doxgen_latex_worker.server:main
