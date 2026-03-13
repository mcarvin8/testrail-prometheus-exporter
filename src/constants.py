"""
Constants Configuration Module

This module defines global constants used across the testrail prometheus exporter.

Constants:
    - REQUESTS_TIMEOUT_SECONDS: HTTP request timeout (300 seconds = 5 minutes)
      Used for all API calls to TestRail to prevent hanging requests

    - TESTRAIL_PAGE_SIZE: Max number of records per API request (250 is TestRail's limit)
      Used when paginating get_tests and similar endpoints

    - BASE_URL: TestRail API base URL
      All API endpoints are appended to this base URL
      Can be set via TESTRAIL_BASE_URL environment variable
      Defaults to empty string if not set (user must provide via env var)
"""

import os

REQUESTS_TIMEOUT_SECONDS = 300
TESTRAIL_PAGE_SIZE = 250
BASE_URL = os.getenv("TESTRAIL_BASE_URL", "")
