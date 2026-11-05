> [!IMPORTANT]
> This repository is archived. doxgen-worker-latex now lives in the doxgen monorepo,
> [adeweb-be/doxgen](https://github.com/adeweb-be/doxgen) (private), in `workers/latex/`.
> Its full history is kept there.

# doxgen-worker

## Security

The worker renders templates that API users upload. It must run on an internal network that only the doxgen API can reach.

- Set `WORKER_TOKEN` to the same value as the API's `WORKER_TOKEN`. The worker does not start without it, and it answers `401` to a generation request without `Authorization: Bearer <WORKER_TOKEN>`.
- `template_path` and `destination_path` must stay under `/storage`. Other paths get `400`.
- Templates render in Jinja's `ImmutableSandboxedEnvironment`, and includes load only from the template's own folder. `pdflatex` runs with `-no-shell-escape`, `openin_any=p` and `openout_any=p` in a temporary folder, so a document cannot read files outside it.
