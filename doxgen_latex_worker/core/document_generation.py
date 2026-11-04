import asyncio
import json
import os
import shutil
import tempfile
from subprocess import Popen

import jinja2
import pypandoc as pypandoc
from asgiref.sync import sync_to_async
from jinja2.sandbox import ImmutableSandboxedEnvironment

from doxgen_latex_worker.core.health import Health
from doxgen_latex_worker.core.responses import response_header, handle_404
from doxgen_latex_worker.core.security import InvalidRequest, is_authorized, storage_path


def html2latex(value):
    return pypandoc.convert_text(value, "latex", format="html")


def md2latex(value):
    return pypandoc.convert_text(value, "latex", format="md")


# kpathsea settings for pdflatex. Paranoid mode ("p") refuses absolute paths and "..",
# so a document can read and write only in its build folder and in the TeX installation.
TEX_ENV = {"openin_any": "p", "openout_any": "p", "shell_escape": "f"}


def make_jinja_env(loader_path):
    # The sandbox blocks access to Python internals from template expressions.
    # The loader sees only the folder of the template, so includes cannot read other templates.
    env = ImmutableSandboxedEnvironment(
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        line_statement_prefix="%%",
        line_comment_prefix="%#",
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(loader_path),
    )
    env.filters["html2latex"] = html2latex
    env.filters["md2latex"] = md2latex
    return env


@sync_to_async
def generate(template_file, generation_context, destination_file):
    env = make_jinja_env(os.path.dirname(template_file))
    template = env.get_template(os.path.basename(template_file))
    compile_tex(template.render(**generation_context), destination_file)


def compile_tex(rendered_tex, out_pdf_path):
    tmp_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmp_dir, "out.tex"), "w") as outfile:
            outfile.write(rendered_tex)
        # Run in the build folder with a relative file name: paranoid mode refuses absolute paths.
        p = Popen(
            ["pdflatex", "-interaction=nonstopmode", "-no-shell-escape", "out.tex"],
            cwd=tmp_dir,
            env={**os.environ, **TEX_ENV},
        )
        p.communicate()
        shutil.move(os.path.join(tmp_dir, "out.pdf"), out_pdf_path)
    finally:
        shutil.rmtree(tmp_dir)


async def read_body(receive):
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    return body


async def send_failure(send, error, status=500):
    await send(response_header("json", status))
    return await send(
        {
            "type": "http.response.body",
            "body": bytes(json.dumps({"status": "failure", "error": error}), "utf-8"),
            "more_body": False,
        }
    )


GENERATION_LOCK = asyncio.Lock()


async def document_generation_view(scope, receive, send):
    if scope["method"] != "POST":
        return await handle_404(scope, receive, send)
    if not is_authorized(scope):
        return await send_failure(send, "Unauthorized", status=401)

    payload = json.loads((await read_body(receive)).decode("utf-8"))
    generation_context = payload["generation_context"]
    try:
        template_file = storage_path(payload["template_path"])
        destination_file = storage_path(payload["destination_path"])
    except InvalidRequest as e:
        return await send_failure(send, str(e), status=400)
    async with GENERATION_LOCK:
        try:
            await asyncio.wait_for(
                generate(template_file, generation_context, destination_file),
                timeout=int(os.getenv("GENERATION_TIMEOUT", default=120)),
            )
        except TimeoutError:
            # Latex is probably stuck
            Health.state = "unhealthy"
            return await send_failure(send, "Generation timed out")
        except Exception as e:
            return await send_failure(send, str(e))

    await send(response_header("json", 200))
    return await send(
        {
            "type": "http.response.body",
            "body": bytes(json.dumps({"status": "success"}), "utf-8"),
            "more_body": False,
        }
    )
