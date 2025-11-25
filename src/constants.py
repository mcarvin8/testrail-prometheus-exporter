"""
Constants Configuration Module

This module defines global constants used across the testrail prometheus exporter.

Constants:
    - REQUESTS_TIMEOUT_SECONDS: HTTP request timeout (300 seconds = 5 minutes)
      Used for all API calls to TestRail to prevent hanging requests
    
    - BASE_URL: TestRail API base URL
      All API endpoints are appended to this base URL
      Can be set via TESTRAIL_BASE_URL environment variable
      Defaults to empty string if not set (user must provide via env var)
"""
import os

REQUESTS_TIMEOUT_SECONDS = 300
BASE_URL = os.getenv('TESTRAIL_BASE_URL', '')
