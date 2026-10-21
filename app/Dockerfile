# IAM-SRA app image: build the Vue app, then serve dist/ and the /api/<tool> proxy with serve_app.py (stdlib only).
# Inside Kubernetes set IAMIQ_IN_CLUSTER=1 so the proxy targets the backends' service names (deploy/iam-sra-ui.yaml).
#
#   docker build -t iam-sra/frontend:local app

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js proxy-routes.json ./
COPY public ./public
COPY src ./src
RUN npx vite build

FROM python:3.12-slim
WORKDIR /app
COPY serve_app.py proxy-routes.json ./
COPY --from=build /app/dist ./dist
ENV PORT=5001 HOST=0.0.0.0 PYTHONDONTWRITEBYTECODE=1
EXPOSE 5001
USER nobody
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('IAM_SRA_UI_PORT', os.environ.get('PORT', '5001')) + '/', timeout=4)"
CMD ["python", "serve_app.py"]
