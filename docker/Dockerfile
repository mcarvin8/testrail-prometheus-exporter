FROM ubuntu:24.04

# Set working directory to scripts
WORKDIR /app/testrail-prometheus-exporter
COPY src /app/testrail-prometheus-exporter

# Copy documentation
COPY README.md /app/testrail-prometheus-exporter
COPY LICENSE.md /app/testrail-prometheus-exporter
COPY version.txt /app/testrail-prometheus-exporter

# Install required dependencies
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv tzdata && \
    python3 -m venv /opt/venv && \
    rm -rf /var/lib/apt/lists/* && \
    /opt/venv/bin/pip install --no-cache-dir prometheus_client requests APScheduler && \
    /opt/venv/bin/pip list

# Create non-root user for running the application
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app /opt/venv

# Set the environment variables to use the venv
ENV PATH="/opt/venv/bin:$PATH" \
    TZ="UTC"

# Run as non-root user
USER appuser

# Run the application
ENTRYPOINT ["python3", "testrail_exporter.py"]
EXPOSE 9001

# Health check: verify metrics endpoint responds (uses METRICS_PORT env, default 9001)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import os, urllib.request; port = os.environ.get('METRICS_PORT', '9001'); urllib.request.urlopen(f'http://localhost:{port}/metrics')" || exit 1
