#!/usr/bin/env bash
# Publish site/ to the desert-hours stack.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -I pipeline/build_site.py
O() { aws cloudformation describe-stacks --region us-east-1 --stack-name desert-hours --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
B=$(O Bucket)
aws s3 sync site "s3://$B" --delete --exclude template.html --exclude '*.geojson' --cache-control max-age=300 --no-progress
for f in tracts reach; do aws s3 cp "site/data/$f.geojson" "s3://$B/data/$f.geojson" --content-type application/json --cache-control max-age=300 --no-progress; done
aws cloudfront create-invalidation --distribution-id "$(O DistributionId)" --paths '/*' --query Invalidation.Id --output text
echo "https://$(O Domain)/"
