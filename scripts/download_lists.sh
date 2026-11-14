#!/usr/bin/env bash
# Downloads OpenSanctions consolidated sanctions data (CC BY-NC 4.0; non-commercial use).
set -euo pipefail
cd "$(dirname "$0")/../data/lists"
curl -fsSL -o sanctions.csv https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv
echo "Downloaded $(wc -l < sanctions.csv) rows"
