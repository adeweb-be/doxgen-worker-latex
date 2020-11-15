from doxgen_latex_worker.core.document_generation import document_generation_view
from doxgen_latex_worker.core.health import healthcheck_view

ROUTES = {"/": document_generation_view, "/healthcheck": healthcheck_view}
