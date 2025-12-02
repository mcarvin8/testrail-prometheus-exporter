"""
TestRail Prometheus Exporter

A general-purpose monitoring script that fetches test execution data from TestRail API
and exposes it as Prometheus metrics for observability and alerting.

Purpose:
    - Continuously polls TestRail API for completed test runs from the past week
    - Retrieves test cases and results for each completed run
    - Exposes test metrics (passed, failed, blocked, retest, untested, etc.) as Prometheus gauges
    - Runs as a long-lived service with APScheduler executing on a configurable schedule

Key Features:
    - Fetches test runs for a configurable project ID
    - Parses test run summaries and individual test results
    - Filters out tests with status_id 10 (untested)
    - Maps test IDs to human-readable titles
    - Provides detailed debug logging for troubleshooting

Prometheus Metrics Exposed:
    - testrail_run_info: Overall test run information with labels
    - test_run_passed_count: Count of passed tests per run
    - test_run_failed_count: Count of failed tests per run
    - test_run_retest_count: Count of tests marked for retest
    - test_run_untested_count: Count of untested tests per run
    - test_run_blocked_count: Count of blocked tests per run
    - testrail_test_result: Individual test result details
    - test_run_<custom_metric_name>_count: Custom status counts (dynamically created based on configuration)

Environment Variables Required:
    - TESTRAIL_API_KEY: TestRail API authentication key
    - TESTRAIL_USERNAME: TestRail username for authentication
    - TESTRAIL_BASE_URL: TestRail API base URL (e.g., "https://yourcompany.testrail.io/index.php?/api/v2/")
    - TESTRAIL_PROJECT_ID: TestRail project ID to monitor

Environment Variables Optional:
    - SCHEDULE_CRON: Cron expression for scheduling (default: "0,12" for 00:00 and 12:00 UTC daily)
                     Format: hour values separated by commas (e.g., "0,6,12,18" for every 6 hours)
    - METRICS_PORT: Port for Prometheus metrics server (default: 9001)
    - LOOKBACK_DAYS: Number of days to look back for test runs (default: 7)
    - CUSTOM_STATUS_CONFIG: Path to JSON file defining custom statuses (default: "custom_statuses.json")

Usage:
    python testrail_exporter.py
    
The service starts a Prometheus HTTP server on the configured port and runs indefinitely.
"""
from datetime import datetime, timezone, timedelta
import os

import requests
from requests.auth import HTTPBasicAuth
from prometheus_client import start_http_server
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from constants import REQUESTS_TIMEOUT_SECONDS, BASE_URL
from logger import logger
from gauges import (test_run_info, test_run_passed_count,
                    test_run_failed_count, test_run_retest_count,
                    test_run_untested_count, test_run_blocked_count,
                    test_result_info, create_custom_status_gauges)
from custom_status_config import load_custom_status_config


def fetch_requested_data(url, auth):
    '''
    Fetches data from the specified URL using an HTTP GET request
    '''
    try:
        response_data = requests.get(url, auth=auth, timeout=REQUESTS_TIMEOUT_SECONDS)
        response_data.raise_for_status()
        return response_data
    except requests.exceptions.RequestException as e:
        logger.error("Error fetching Requested data: %s", e)
        return None


def format_timestamp(timestamp):
    '''Converts a Unix timestamp to a formatted date string.'''
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def expose_test_reports(auth, project_id, lookback_days, custom_status_gauges=None):
    '''
    Retrieve the test runs from TestRail tool and
    expose test run report
    
    Args:
        auth: HTTPBasicAuth object for TestRail authentication
        project_id: TestRail project ID to monitor
        lookback_days: Number of days to look back for test runs
        custom_status_gauges: Dictionary mapping field_name to Gauge objects for custom statuses
    '''
    logger.info('Test Report function started...')
    test_run_info.clear()
    test_run_passed_count.clear()
    test_run_failed_count.clear()
    test_run_retest_count.clear()
    test_run_untested_count.clear()
    test_run_blocked_count.clear()
    test_result_info.clear()
    
    # Clear custom status gauges if they exist
    if custom_status_gauges:
        for gauge in custom_status_gauges.values():
            gauge.clear()

    today = datetime.now(timezone.utc)
    past_period = today - timedelta(days=lookback_days)
    start_timestamp = int(past_period.timestamp())
    now = int(today.timestamp())

    # Update endpoint URL to get only test runs created in the lookback period
    test_runs_endpoint = f"{BASE_URL}get_runs/{project_id}&created_after={start_timestamp}&created_before={now}"

    try:
        runs_response = fetch_requested_data(test_runs_endpoint, auth)
        runs = runs_response.json()
    except ValueError as e:
        logger.error("Error decoding JSON response: %s", e)
        return

    for runx in runs.get('runs', []):
        if runx.get('is_completed', False):
            logger.debug("Parsing test run: ID=%s, Name=%s", runx['id'], runx.get('name', ''))

            created_datex = format_timestamp(runx['created_on'])

            test_run_info.labels(run_id=runx['id'], created_date=created_datex, name=runx['name'],
                    passed=runx['passed_count'], failed=runx['failed_count'],
                    retest=runx['retest_count'], untested=runx['untested_count'],
                    blocked=runx['blocked_count']).set(1)

            test_run_passed_count.labels(run_id=runx['id'],
                                         created_date=created_datex).set(runx['passed_count'])
            test_run_failed_count.labels(run_id=runx['id'],
                                         created_date=created_datex).set(runx['failed_count'])
            test_run_retest_count.labels(run_id=runx['id'],
                                         created_date=created_datex).set(runx['retest_count'])
            test_run_untested_count.labels(run_id=runx['id'],
                                           created_date=created_datex).set(runx['untested_count'])
            test_run_blocked_count.labels(run_id=runx['id'],
                                          created_date=created_datex).set(runx['blocked_count'])

            # Handle custom status counts
            if custom_status_gauges:
                for field_name, gauge in custom_status_gauges.items():
                    # Check if the field exists in the run data
                    if field_name in runx:
                        count_value = runx.get(field_name, 0)
                        gauge.labels(run_id=runx['id'],
                                    created_date=created_datex).set(count_value)
                        logger.debug("Set custom status %s=%d for run ID=%s", 
                                    field_name, count_value, runx['id'])

            test_id_to_title = {}

            test_cases_endpoint = f"{BASE_URL}get_tests/{runx['id']}"

            try:
                tests_response = fetch_requested_data(test_cases_endpoint, auth)
                test_cases = tests_response.json()
                logger.debug("Parsing %d test cases for run ID=%s", len(test_cases.get('tests', [])), runx['id'])
                for test_case in test_cases['tests']:
                    logger.debug("Parsing test case: ID=%s, Title=%s", test_case['id'], test_case['title'])
                    test_id_to_title[test_case['id']] = test_case['title']
            except ValueError as e:
                logger.error("Error decoding JSON response for test cases: %s", e)
                continue

            test_results_endpoint = f"{BASE_URL}get_results_for_run/{runx['id']}"

            try:
                results_response = fetch_requested_data(test_results_endpoint, auth=auth)
                test_results = results_response.json()
                logger.debug("Parsing %d test results for run ID=%s", len(test_results.get('results', [])), runx['id'])
                for result in test_results.get('results', []):
                    if result['status_id'] != 10:
                        title = test_id_to_title.get(result['test_id'], "Unknown Title")
                        created_date = format_timestamp(result['created_on'])
                        logger.debug("Parsing test result: Test ID=%s, Title=%s, Status=%s", 
                                     result['test_id'], title, result['status_id'])

                        test_result_info.labels(run_id=runx['id'], test_id=result['test_id'],
                                                title=title,
                                                status_id=result['status_id'],
                                                created_date=created_date,
                                                comment=result['comment']).set(1)
            except ValueError as e:
                logger.error("Error decoding JSON response for test results: %s", e)
                continue


if __name__ == '__main__':
    # Validate required environment variables
    API_KEY = os.getenv('TESTRAIL_API_KEY')
    USERNAME = os.getenv('TESTRAIL_USERNAME')
    PROJECT_ID = os.getenv('TESTRAIL_PROJECT_ID')
    
    if not API_KEY:
        logger.error('TESTRAIL_API_KEY environment variable is required')
        raise ValueError('TESTRAIL_API_KEY environment variable is required')
    if not USERNAME:
        logger.error('TESTRAIL_USERNAME environment variable is required')
        raise ValueError('TESTRAIL_USERNAME environment variable is required')
    if not BASE_URL:
        logger.error('TESTRAIL_BASE_URL environment variable is required')
        raise ValueError('TESTRAIL_BASE_URL environment variable is required')
    if not PROJECT_ID:
        logger.error('TESTRAIL_PROJECT_ID environment variable is required')
        raise ValueError('TESTRAIL_PROJECT_ID environment variable is required')
    
    try:
        PROJECT_ID = int(PROJECT_ID)
    except ValueError:
        logger.error('TESTRAIL_PROJECT_ID must be a valid integer')
        raise ValueError('TESTRAIL_PROJECT_ID must be a valid integer')
    
    # Get optional environment variables with defaults
    SCHEDULE_CRON = os.getenv('SCHEDULE_CRON', '0,12')
    METRICS_PORT = int(os.getenv('METRICS_PORT', '9001'))
    LOOKBACK_DAYS = int(os.getenv('LOOKBACK_DAYS', '7'))
    CUSTOM_STATUS_CONFIG_PATH = os.getenv('CUSTOM_STATUS_CONFIG', 'custom_statuses.json')
    
    # Load custom status configuration
    custom_status_config = load_custom_status_config(CUSTOM_STATUS_CONFIG_PATH)
    custom_status_gauges = create_custom_status_gauges(custom_status_config) if custom_status_config else None
    
    logger.info('Configuration loaded:')
    logger.info('  TestRail Base URL: %s', BASE_URL)
    logger.info('  Project ID: %s', PROJECT_ID)
    logger.info('  Schedule: %s (UTC hours)', SCHEDULE_CRON)
    logger.info('  Prometheus Port: %s', METRICS_PORT)
    logger.info('  Lookback Days: %s', LOOKBACK_DAYS)
    if custom_status_gauges:
        logger.info('  Custom Statuses: %d configured', len(custom_status_gauges))
    else:
        logger.info('  Custom Statuses: None configured')
    
    # Start Prometheus HTTP server
    start_http_server(METRICS_PORT)
    logger.info('Prometheus metrics server started on port %s', METRICS_PORT)
    
    # Get authentication credentials
    authentication = HTTPBasicAuth(username=USERNAME, password=API_KEY)

    # Create scheduler with timezone-aware settings
    scheduler = BlockingScheduler(timezone='UTC')
    
    # Schedule the job to run at configured hours
    scheduler.add_job(
        func=lambda: expose_test_reports(authentication, PROJECT_ID, LOOKBACK_DAYS, custom_status_gauges),
        trigger=CronTrigger(hour=SCHEDULE_CRON, timezone='UTC'),
        id='test_reports_job',
        name='Fetch and expose TestRail reports',
        replace_existing=True
    )
    
    logger.info('Scheduler configured to run at hours %s UTC daily', SCHEDULE_CRON)
    
    # Run the job immediately on startup
    logger.info('Running initial test report collection...')
    expose_test_reports(authentication, PROJECT_ID, LOOKBACK_DAYS, custom_status_gauges)
    
    # Start the scheduler (this blocks and keeps the script running)
    logger.info('Starting scheduler...')
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Scheduler shutdown requested')
        scheduler.shutdown()
        logger.info('Scheduler stopped gracefully')
