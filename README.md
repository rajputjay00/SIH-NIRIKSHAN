---
title: Nirikshan
sdk: docker
app_port: 7860
---

# Nirikshan

Nirikshan (निरीक्षण) is a rules-as-code compliance checking engine and image scanning web application for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011.

## Quick Start (Docker)

```bash
docker build -t nirikshan .
docker run -p 7860:7860 nirikshan
```

Visit `http://localhost:7860/` for the local web app and `http://localhost:7860/api/health` for the local API status.

## Live Deployment (Azure Container Apps)
- **Live Web App**: [https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io/](https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io/)
- **Live Health API**: [https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io/api/health](https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io/api/health)

