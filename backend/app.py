import gradio as gr
import uvicorn
from main import app  # FastAPI app with CORS, /health and /scan already defined

with gr.Blocks() as demo:
    gr.Markdown("# Nirikshan API\nRunning. Endpoints: `/health`, `/scan`")

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
