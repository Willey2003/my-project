# otel-demo image. Built and pushed by ../../up.sh otel:
#   docker build -t localhost:5001/otel-demo:0.1 lab/golden/observability/otel/app && docker push localhost:5001/otel-demo:0.1
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
# opentelemetry-bootstrap detects installed libraries (flask, requests...) and installs their instrumentations
RUN pip install -r requirements.txt && opentelemetry-bootstrap -a install
COPY app.py .
RUN useradd -u 10001 -r app
USER 10001
EXPOSE 5000
# zero-code instrumentation: the SDK is configured entirely by OTEL_* env vars (see deployment.yaml)
CMD ["opentelemetry-instrument", "python", "app.py"]
