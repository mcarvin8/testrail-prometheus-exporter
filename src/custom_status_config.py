"""
Custom Status Configuration Module

This module handles loading and parsing custom status configurations from JSON files.
Custom statuses allow users to track additional test statuses beyond the standard
passed, failed, blocked, retest, and untested statuses.

Configuration Format:
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

The field_name should match the field name in the TestRail API response (e.g., "custom_status5_count").
The metric_name is used to create the Prometheus metric name (e.g., "test_run_skipped_count").
"""
import json
import os
from logger import logger


def load_custom_status_config(config_path=None):
    """
    Load custom status configuration from a JSON file.
    
    Args:
        config_path: Path to the JSON configuration file. If None, checks
                     CUSTOM_STATUS_CONFIG environment variable or defaults to
                     'custom_statuses.json' in the current directory.
    
    Returns:
        dict: Dictionary mapping field_name to status configuration, or empty dict if
              no config file is found or invalid.
    
    Example return:
        {
            "custom_status5_count": {
                "status_id": 5,
                "field_name": "custom_status5_count",
                "metric_name": "skipped",
                "description": "Number of skipped tests"
            }
        }
    """
    if config_path is None:
        config_path = os.getenv('CUSTOM_STATUS_CONFIG', 'custom_statuses.json')
    
    if not os.path.exists(config_path):
        logger.debug("Custom status config file not found at %s, skipping custom statuses", config_path)
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        custom_statuses = config.get('custom_statuses', [])
        if not custom_statuses:
            logger.warning("Custom status config file %s contains no custom_statuses", config_path)
            return {}
        
        # Create a dictionary mapping field_name to status config
        status_map = {}
        for status in custom_statuses:
            field_name = status.get('field_name')
            if not field_name:
                logger.warning("Custom status entry missing 'field_name', skipping: %s", status)
                continue
            
            status_map[field_name] = {
                'status_id': status.get('status_id'),
                'field_name': field_name,
                'metric_name': status.get('metric_name', field_name.replace('_count', '')),
                'description': status.get('description', f"Number of {status.get('metric_name', field_name)} tests")
            }
        
        logger.info("Loaded %d custom status(es) from %s", len(status_map), config_path)
        return status_map
    
    except json.JSONDecodeError as e:
        logger.error("Error parsing custom status config file %s: %s", config_path, e)
        return {}
    except Exception as e:
        logger.error("Error loading custom status config file %s: %s", config_path, e)
        return {}

