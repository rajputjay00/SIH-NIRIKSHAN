import os
import threading
import time

import gradio as gr
from main import app as api  # FastAPI app with CORS, /health and /scan

with gr.Blocks() as demo:
    gr.Markdown("# Nirikshan API\nRunning. Endpoints: `/api/health`, `/api/scan`")


def _attach_api():
    # Wait until Gradio's server exists, then mount our FastAPI app under /api
    for _ in range(600):
        server_app = getattr(demo, "server_app", None) or getattr(demo, "app", None)
        if server_app is not None:
            server_app.mount("/api", api)
            return
        time.sleep(0.5)


threading.Thread(target=_attach_api, daemon=True).start()

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
    )
