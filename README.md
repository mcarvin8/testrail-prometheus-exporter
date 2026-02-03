# TestRail Prometheus Exporter

![Docker Image Version (latest by date)](https://img.shields.io/docker/v/mcarvin8/testrail-prometheus-exporter?sort=date)
![Docker Pulls](https://img.shields.io/docker/pulls/mcarvin8/testrail-prometheus-exporter)
![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/mcarvin8/testrail-prometheus-exporter)

A Prometheus exporter that fetches test execution data from TestRail API and exposes it as Prometheus metrics for observability and alerting.

## Overview

The TestRail Prometheus Exporter continuously polls the TestRail API for completed test runs and exposes detailed test metrics as Prometheus gauges. It runs as a long-lived service with configurable scheduling using APScheduler.

## Features

- Fetches test runs for a configurable project ID
- Retrieves test cases and results for each completed run
- Exposes comprehensive test metrics (passed, failed, blocked, retest, untested, etc.) as Prometheus gauges
- Configurable scheduling via cron expressions
- Filters out untested tests (status_id 10)
- Maps test IDs to human-readable titles
- Detailed debug logging for troubleshooting

## Prometheus Metrics

The exporter exposes the following metrics:

- `testrail_run_info`: Overall test run information with labels (run_id, created_date, name, passed, failed, retest, untested, blocked)
- `test_run_passed_count`: Count of passed tests per run
- `test_run_failed_count`: Count of failed tests per run
- `test_run_retest_count`: Count of tests marked for retest
- `test_run_untested_count`: Count of untested tests per run
- `test_run_blocked_count`: Count of blocked tests per run
- `testrail_test_result`: Individual test result details with labels (run_id, test_id, title, status_id, created_date, comment)
- `test_run_<custom_metric_name>_count`: Custom status counts (dynamically created based on configuration)

## Quick Start

### Using Docker

Pull and run the Docker image:

```bash
docker run -d \
  --name testrail-exporter \
  -p 9001:9001 \
  -e TESTRAIL_API_KEY="your-api-key" \
  -e TESTRAIL_USERNAME="your-username" \
  -e TESTRAIL_BASE_URL="https://yourcompany.testrail.io/index.php?/api/v2/" \
  -e TESTRAIL_PROJECT_ID="1" \
  mcarvin8/testrail-prometheus-exporter
```

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  testrail-exporter:
    image: mcarvin8/testrail-prometheus-exporter
    container_name: testrail-exporter
    ports:
      - "9001:9001"
    environment:
      - TESTRAIL_API_KEY=${TESTRAIL_API_KEY}
      - TESTRAIL_USERNAME=${TESTRAIL_USERNAME}
      - TESTRAIL_BASE_URL=${TESTRAIL_BASE_URL}
      - TESTRAIL_PROJECT_ID=${TESTRAIL_PROJECT_ID}
      # Optional variables
      - SCHEDULE_CRON=0,12
      - METRICS_PORT=9001
      - LOOKBACK_DAYS=7
    restart: unless-stopped
```

Then run:

```bash
docker-compose up -d
```

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TESTRAIL_API_KEY` | TestRail API authentication key | `abc123xyz789` |
| `TESTRAIL_USERNAME` | TestRail username for authentication | `user@example.com` |
| `TESTRAIL_BASE_URL` | TestRail API base URL | `https://yourcompany.testrail.io/index.php?/api/v2/` |
| `TESTRAIL_PROJECT_ID` | TestRail project ID to monitor | `1` |

### Optional Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SCHEDULE_CRON` | Cron expression for scheduling (UTC hours, comma-separated) | `0,12` | `0,6,12,18` (every 6 hours) |
| `METRICS_PORT` | Port for Prometheus metrics server | `9001` | `9090` |
| `LOOKBACK_DAYS` | Number of days to look back for test runs | `7` | `14` |
| `CUSTOM_STATUS_CONFIG` | Path to JSON file defining custom statuses | `custom_statuses.json` | `/config/custom_statuses.json` |

### Custom Status Configuration

The exporter supports custom test statuses beyond the standard passed, failed, blocked, retest, and untested statuses. This is useful for teams that have custom statuses like "skipped" or other status-specific metrics.

To configure custom statuses, create a JSON file (default: `custom_statuses.json`) with the following format:

```json
{
  "custom_statuses": [
    {
      "status_id": 5,
      "field_name": "custom_status5_count",
      "metric_name": "skipped",
      "description": "Number of skipped tests"
    }
  ]
}
```

**Configuration Fields:**
- `status_id`: The TestRail status ID (optional, for reference)
- `field_name`: The exact field name as returned by the TestRail API (e.g., `custom_status5_count`)
- `metric_name`: The name used in the Prometheus metric (e.g., `skipped` creates `test_run_skipped_count`)
- `description`: Description for the Prometheus metric

**Example:**
If you configure a custom status with `field_name: "custom_status5_count"` and `metric_name: "skipped"`, the exporter will:
- Look for `custom_status5_count` in the TestRail API response
- Create a Prometheus metric named `test_run_skipped_count`
- Expose the count with labels `run_id` and `created_date`

**Note:** The `field_name` must exactly match the field name returned by the TestRail API. You can find these field names by inspecting the TestRail API response for test runs.

### Scheduling

The exporter uses cron-based scheduling to fetch data from TestRail. By default, it runs at 00:00 and 12:00 UTC daily. You can customize this using the `SCHEDULE_CRON` environment variable.

**Format**: Comma-separated hour values (0-23) in UTC

**Examples**:
- `0,12` - Run at midnight and noon UTC (default)
- `0,6,12,18` - Run every 6 hours
- `0` - Run once daily at midnight UTC
- `*/6` - Run every 6 hours (0, 6, 12, 18)

**Note**: The exporter runs an initial data collection immediately on startup, then follows the scheduled intervals.
