# Azure Container Apps Deployment Guide

## Live Application URL
- **Production URL**: [https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io/](https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io/)
- **Health Check Endpoint**: [https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io/api/health](https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io/api/health)

## Deploying New Container Image Versions
To deploy an updated container image version built by CI, run:

```bash
az containerapp update -n nirikshan -g nirikshan-rg --image ghcr.io/rajputjay00/nirikshan:<sha>
```

## Demo Day Optimization (Eliminate Cold Starts)
By default, `--min-replicas` is set to `0` to minimize resource consumption when idle. For demo days or live evaluation, set `--min-replicas` to `1` to keep at least one instance warm and eliminate cold starts:

```bash
az containerapp update -n nirikshan -g nirikshan-rg --min-replicas 1
```

To revert to scale-to-zero mode after demo days:
```bash
az containerapp update -n nirikshan -g nirikshan-rg --min-replicas 0
```
