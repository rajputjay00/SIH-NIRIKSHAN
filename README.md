---
title: Nirikshan
sdk: docker
app_port: 7860
hardware: cpu-basic
---

# Nirikshan

Nirikshan (निरीक्षण) is a rules-as-code compliance checking engine and image scanning web application for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011.

## Quick Start (Docker)

```bash
docker build -t nirikshan .
docker run -p 7860:7860 nirikshan
```

Visit `http://localhost:7860/` for the web app and `http://localhost:7860/api/health` for the API status.
