FROM ubuntu:latest

# Set working directory to scripts
WORKDIR /app/testrail-prometheus-exporter
COPY src /app/testrail-prometheus-exporter

# Copy documentation
COPY README.md /app/testrail-prometheus-exporter
COPY LICENSE.md /app/testrail-prometheus-exporter
COPY version.txt /app/testrail-prometheus-exporter

# Install required dependencies
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv && \
    python3 -m venv /opt/venv && \
    rm -rf /var/lib/apt/lists/* && \
    /opt/venv/bin/pip install --no-cache-dir prometheus_client requests APScheduler && \
    /opt/venv/bin/pip list

# Set the environment variables to use the venv
ENV PATH="/opt/venv/bin:$PATH"

# Run the application
ENTRYPOINT ["python3", "testrail_exporter.py"]
EXPOSE 9001
