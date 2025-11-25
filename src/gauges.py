"""
Prometheus Metrics Definition Module

This module defines all Prometheus Gauge metrics that are exposed by the testrail prometheus exporter.
These metrics track TestRail test execution data and can be scraped by Prometheus for
monitoring, alerting, and visualization in Grafana dashboards.

Metrics Defined:
    - test_run_info: High-level summary of each test run with multiple labels
    - test_run_passed_count: Count of passed tests per run
    - test_run_failed_count: Count of failed tests per run
    - test_run_retest_count: Count of tests marked for retest per run
    - test_run_untested_count: Count of untested tests per run
    - test_run_blocked_count: Count of blocked tests per run
    - test_result_info: Detailed information about individual test results

All gauges use labels to provide dimensional data that can be queried and filtered
in Prometheus queries and Grafana visualizations.
"""
from prometheus_client import Gauge


test_run_info = Gauge('testrail_run_info', 'Information about test runs',
                      ['run_id', 'name', 'created_date', 'passed', 'failed', 'retest', 'untested', 'blocked'])

test_run_passed_count = Gauge('test_run_passed_count', 'Number of passed tests', ['run_id', 'created_date'])
test_run_failed_count = Gauge('test_run_failed_count', 'Number of failed tests', ['run_id', 'created_date'])
test_run_retest_count = Gauge('test_run_retest_count', 'Number of tests to retest', ['run_id', 'created_date'])
test_run_untested_count = Gauge('test_run_untested_count', 'Number of untested tests', ['run_id', 'created_date'])
test_run_blocked_count = Gauge('test_run_blocked_count', 'Number of blocked tests', ['run_id', 'created_date'])

test_result_info = Gauge('testrail_test_result', 'Information about individual test results',
                         ['run_id','test_id', 'title', 'status_id', 'created_date', 'comment'])
