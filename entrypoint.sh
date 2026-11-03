#!/bin/sh
exec gunicorn -k uvicorn_worker.UvicornWorker -c uvicorn_conf.py  doxgen_latex_worker.server:main
