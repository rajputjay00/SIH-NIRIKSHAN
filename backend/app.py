try:
    import spaces
except ImportError:
    spaces = None

import os

import gradio as gr
from starlette.routing import Mount

from main import app as api  # FastAPI app with CORS, /health and /scan


def _gpu_noop():
    return "ok"


if spaces is not None:
    _gpu_noop = spaces.GPU(_gpu_noop)

with gr.Blocks() as demo:
    gr.Markdown("# Nirikshan API\nRunning. Endpoints: `/api/health`, `/api/scan`")
    _btn = gr.Button("noop", visible=False)
    _out = gr.Textbox(visible=False)
    _btn.click(_gpu_noop, None, _out)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
        ssr_mode=False,
        app_kwargs={"routes": [Mount("/api", app=api)]},
    )
