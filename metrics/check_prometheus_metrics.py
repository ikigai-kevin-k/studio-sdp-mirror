#!/usr/bin/env python3
"""
Script to check Prometheus metrics using PromQL API
Verifies that metrics are correctly pushed to Prometheus
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Prometheus API endpoint
PROMETHEUS_URL = "http://100.64.0.113:9090"
PUSHGATEWAY_URL = "http://100.64.0.113:9091"

# Job name
JOB_NAME = "time_intervals_metrics"

# Instance labels to check
INSTANCES = ["api-instance", "aro22"]

# Time range for query (last 1 hour)
TIME_RANGE = "1h"


def query_prometheus(promql_query: str, timeout: int = 30):
    """
    Query Prometheus using PromQL API
    
    Args:
        promql_query: PromQL query string
        timeout: Request timeout in seconds
        
    Returns:
        dict: Query result or None if failed
    """
    try:
        url = f"{PROMETHEUS_URL}/api/v1/query"
        params = {
            "query": promql_query
        }
        
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"✗ Error querying Prometheus: {e}")
        return None


def query_prometheus_range(promql_query: str, start_time: str, end_time: str, step: str = "15s", timeout: int = 30):
    """
    Query Prometheus using PromQL range query API
    
    Args:
        promql_query: PromQL query string
        start_time: Start time (RFC3339 or Unix timestamp)
        end_time: End time (RFC3339 or Unix timestamp)
        step: Query resolution step width (e.g., "15s")
        timeout: Request timeout in seconds
        
    Returns:
        dict: Query result or None if failed
    """
    try:
        url = f"{PROMETHEUS_URL}/api/v1/query_range"
        params = {
            "query": promql_query,
            "start": start_time,
            "end": end_time,
            "step": step
        }
        
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"✗ Error querying Prometheus range: {e}")
        return None


def check_pushgateway_metrics():
    """
    Check metrics directly from Pushgateway
    
    Returns:
        dict: Pushgateway metrics or None if failed
    """
    try:
        url = f"{PUSHGATEWAY_URL}/metrics"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"✗ Error querying Pushgateway: {e}")
        return None


def check_metric_exists(metric_name: str, instance_label: str):
    """
    Check if a specific metric exists in Prometheus
    
    Args:
        metric_name: Name of the metric
        instance_label: Instance label value
        
    Returns:
        bool: True if metric exists, False otherwise
    """
    query = f'{metric_name}{{job="{JOB_NAME}", instance="{instance_label}"}}'
    
    print(f"\n  Query: {query}")
    result = query_prometheus(query)
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        result_type = data.get("resultType")
        results = data.get("result", [])
        
        if results:
            print(f"  ✓ Found {len(results)} result(s)")
            for item in results:
                metric = item.get("metric", {})
                value = item.get("value", [None, None])
                print(f"    - Instance: {metric.get('instance', 'N/A')}")
                print(f"    - Value: {value[1] if value[1] else 'N/A'}")
                print(f"    - Timestamp: {datetime.fromtimestamp(value[0]) if value[0] else 'N/A'}")
            return True
        else:
            print(f"  ✗ No results found")
            return False
    else:
        print(f"  ✗ Query failed or returned error")
        if result:
            print(f"    Status: {result.get('status')}")
            if result.get("error"):
                print(f"    Error: {result.get('error')}")
        return False


def check_all_metrics_for_instance(instance_label: str):
    """
    Check all time interval metrics for a specific instance
    
    Args:
        instance_label: Instance label value
        
    Returns:
        dict: Dictionary of metric existence status
    """
    print(f"\n{'='*60}")
    print(f"Checking metrics for instance: {instance_label}")
    print(f"{'='*60}")
    
    metrics = [
        "finish_to_start_time",
        "start_to_launch_time",
        "launch_to_deal_time",
        "deal_to_finish_time"
    ]
    
    results = {}
    
    for metric_name in metrics:
        print(f"\n📊 Checking {metric_name}...")
        exists = check_metric_exists(metric_name, instance_label)
        results[metric_name] = exists
    
    return results


def check_pushgateway():
    """
    Check Pushgateway directly for metrics
    """
    print(f"\n{'='*60}")
    print(f"Checking Pushgateway directly")
    print(f"{'='*60}")
    print(f"URL: {PUSHGATEWAY_URL}/metrics")
    
    metrics_text = check_pushgateway_metrics()
    
    if metrics_text:
        print(f"✓ Successfully retrieved metrics from Pushgateway")
        
        # Check if our job name appears
        if JOB_NAME in metrics_text:
            print(f"✓ Found job '{JOB_NAME}' in Pushgateway")
            
            # Count occurrences of our metrics
            metric_names = [
                "finish_to_start_time",
                "start_to_launch_time",
                "launch_to_deal_time",
                "deal_to_finish_time"
            ]
            
            for metric_name in metric_names:
                count = metrics_text.count(f"{metric_name}{{")
                if count > 0:
                    print(f"  ✓ Found {metric_name} ({count} occurrence(s))")
                else:
                    print(f"  ✗ {metric_name} not found")
            
            # Check for instance labels
            for instance in INSTANCES:
                if f'instance="{instance}"' in metrics_text:
                    print(f"  ✓ Found instance '{instance}'")
                else:
                    print(f"  ✗ Instance '{instance}' not found")
        else:
            print(f"✗ Job '{JOB_NAME}' not found in Pushgateway")
        
        # Show last few lines of metrics for debugging
        print(f"\n📋 Last 20 lines of Pushgateway metrics:")
        lines = metrics_text.split('\n')
        for line in lines[-20:]:
            if line.strip() and not line.startswith('#'):
                print(f"  {line}")
    else:
        print(f"✗ Failed to retrieve metrics from Pushgateway")


def check_all_jobs():
    """
    Check what jobs are available in Prometheus
    """
    print(f"\n{'='*60}")
    print(f"Checking available jobs in Prometheus")
    print(f"{'='*60}")
    
    query = 'up{job=~".*"}'
    result = query_prometheus(query)
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        results = data.get("result", [])
        
        jobs = set()
        for item in results:
            metric = item.get("metric", {})
            job = metric.get("job")
            if job:
                jobs.add(job)
        
        print(f"✓ Found {len(jobs)} unique job(s):")
        for job in sorted(jobs):
            print(f"  - {job}")
        
        if JOB_NAME in jobs:
            print(f"\n✓ Job '{JOB_NAME}' is available in Prometheus")
        else:
            print(f"\n✗ Job '{JOB_NAME}' is NOT available in Prometheus")
    else:
        print(f"✗ Failed to query Prometheus for jobs")


def main():
    """Main function"""
    print("="*60)
    print("Prometheus Metrics Checker")
    print("="*60)
    print(f"Prometheus URL: {PROMETHEUS_URL}")
    print(f"Pushgateway URL: {PUSHGATEWAY_URL}")
    print(f"Job name: {JOB_NAME}")
    print(f"Instance labels: {', '.join(INSTANCES)}")
    print("="*60)
    
    # Check Prometheus connectivity
    print("\n🔍 Checking Prometheus connectivity...")
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/status/config", timeout=5)
        if response.status_code == 200:
            print("✓ Prometheus is accessible")
        else:
            print(f"✗ Prometheus returned status code: {response.status_code}")
    except Exception as e:
        print(f"✗ Cannot connect to Prometheus: {e}")
        print(f"  Please check if Prometheus is running at {PROMETHEUS_URL}")
        return
    
    # Check Pushgateway connectivity
    print("\n🔍 Checking Pushgateway connectivity...")
    try:
        response = requests.get(f"{PUSHGATEWAY_URL}/metrics", timeout=5)
        if response.status_code == 200:
            print("✓ Pushgateway is accessible")
        else:
            print(f"✗ Pushgateway returned status code: {response.status_code}")
    except Exception as e:
        print(f"✗ Cannot connect to Pushgateway: {e}")
        print(f"  Please check if Pushgateway is running at {PUSHGATEWAY_URL}")
        return
    
    # Check all jobs
    check_all_jobs()
    
    # Check Pushgateway directly
    check_pushgateway()
    
    # Check metrics for each instance
    all_results = {}
    for instance in INSTANCES:
        results = check_all_metrics_for_instance(instance)
        all_results[instance] = results
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    
    for instance, results in all_results.items():
        print(f"\nInstance: {instance}")
        found_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        print(f"  Metrics found: {found_count}/{total_count}")
        
        for metric_name, exists in results.items():
            status = "✓" if exists else "✗"
            print(f"  {status} {metric_name}")
    
    print("\n" + "="*60)
    print("Check complete!")
    print("="*60)


if __name__ == "__main__":
    main()

