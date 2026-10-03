#!/bin/bash
# Batch billing pipeline runner
set -e
export PIPELINE_ENV="production"
echo "Starting billing sync..."
python src/billing/invoice.py --batch | grep -v "DEBUG"
