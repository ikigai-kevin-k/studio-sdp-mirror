#!/bin/bash
# Quick script to query Prometheus metrics for aro22 instance
# Usage: ./query_aro22_metrics.sh [metric_name]

PROMETHEUS_URL="http://100.64.0.113:9090"
JOB_NAME="time_intervals_metrics"
INSTANCE="aro22"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to query a single metric
query_metric() {
    local metric_name=$1
    echo -e "${YELLOW}Querying: ${metric_name}{job=\"${JOB_NAME}\", instance=\"${INSTANCE}\"}${NC}"
    
    result=$(curl -s -G "${PROMETHEUS_URL}/api/v1/query" \
        --data-urlencode "query=${metric_name}{job=\"${JOB_NAME}\", instance=\"${INSTANCE}\"}")
    
    # Check if query was successful
    status=$(echo "$result" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null)
    
    if [ "$status" = "success" ]; then
        # Extract value
        value=$(echo "$result" | python3 -c "import sys, json; data=json.load(sys.stdin); result=data.get('data', {}).get('result', []); print(result[0].get('value', [None, None])[1] if result else 'N/A')" 2>/dev/null)
        
        if [ "$value" != "N/A" ] && [ -n "$value" ]; then
            echo -e "${GREEN}✓ Value: ${value}${NC}"
            echo "$result" | python3 -m json.tool 2>/dev/null || echo "$result"
        else
            echo "✗ No data found"
        fi
    else
        echo "✗ Query failed"
        echo "$result" | python3 -m json.tool 2>/dev/null || echo "$result"
    fi
    echo ""
}

# If metric name provided, query only that metric
if [ -n "$1" ]; then
    query_metric "$1"
    exit 0
fi

# Otherwise, query all metrics
echo "============================================================"
echo "Querying Prometheus Metrics for ARO22"
echo "============================================================"
echo "Prometheus URL: ${PROMETHEUS_URL}"
echo "Job: ${JOB_NAME}"
echo "Instance: ${INSTANCE}"
echo "============================================================"
echo ""

# Query all metrics
query_metric "finish_to_start_time"
query_metric "start_to_launch_time"
query_metric "launch_to_deal_time"
query_metric "deal_to_finish_time"
query_metric "game_duration_aro22"

echo "============================================================"
echo "Query complete!"
echo "============================================================"
echo ""
echo "Usage examples:"
echo "  # Query all metrics:"
echo "  ./query_aro22_metrics.sh"
echo ""
echo "  # Query specific metric:"
echo "  ./query_aro22_metrics.sh finish_to_start_time"
echo ""
echo "  # Query using curl directly:"
echo "  curl -s -G \"${PROMETHEUS_URL}/api/v1/query\" --data-urlencode 'query=finish_to_start_time{job=\"${JOB_NAME}\", instance=\"${INSTANCE}\"}'"
echo ""


