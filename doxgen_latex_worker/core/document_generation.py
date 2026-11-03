import asyncio
import json
import os
import shutil
import tempfile
from subprocess import Popen

import jinja2
import pypandoc as pypandoc
from asgiref.sync import sync_to_async

from doxgen_latex_worker.core.health import Health
from doxgen_latex_worker.core.responses import response_header, handle_404


def html2latex(value):
    return pypandoc.convert_text(value, "latex", format="html")


def md2latex(value):
    return pypandoc.convert_text(value, "latex", format="md")


latex_jinja_env = jinja2.Environment(
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
    loader=jinja2.FileSystemLoader(os.path.abspath("/storage")),
)
latex_jinja_env.filters["html2latex"] = html2latex
latex_jinja_env.filters["md2latex"] = md2latex


@sync_to_async
def generate(template_path, generation_context, destination_path):
    template = latex_jinja_env.get_template(template_path)
    compile_tex(template.render(**generation_context), "/storage/" + destination_path)


def compile_tex(rendered_tex, out_pdf_path):
    tmp_dir = tempfile.mkdtemp()
    try:
        in_tmp_path = os.path.join(tmp_dir, "out.tex")
        with open(in_tmp_path, "w") as outfile:
            outfile.write(rendered_tex)
        out_tmp_path = os.path.join(tmp_dir, "out.pdf")
        p = Popen(["pdflatex", "-interaction=nonstopmode", f"-output-directory={tmp_dir}", in_tmp_path])
        p.communicate()
        shutil.move(out_tmp_path, out_pdf_path)
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


async def send_failure(send, error):
    await send(response_header("json", 500))
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

    payload = json.loads((await read_body(receive)).decode("utf-8"))
    template_path = payload["template_path"]
    generation_context = payload["generation_context"]
    destination_path = payload["destination_path"]
    async with GENERATION_LOCK:
        try:
            await asyncio.wait_for(
                generate(template_path, generation_context, destination_path),
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
