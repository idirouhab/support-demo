FROM python:3.12-slim
RUN pip install --no-cache-dir python-dotenv==1.2.1 && useradd --uid 10001 --create-home webhook
WORKDIR /app/scripts/openai_gitlab_cloud
# Explicit copy list: .env, .state.json and unrelated repository work never enter the image.
COPY cloud.py gitlab_bridge.py webhook.py reviewer.md merger.md ./
RUN mkdir /data && chown webhook:webhook /data
USER webhook
ENV WEBHOOK_HOST=0.0.0.0 PORT=8080 WEBHOOK_DATA_DIR=/data PYTHONUNBUFFERED=1
EXPOSE 8080
VOLUME /data
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"
CMD ["python", "webhook.py"]
