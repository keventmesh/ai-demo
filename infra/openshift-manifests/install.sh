#!/usr/bin/env bash

current_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
manifests_dir="${current_dir}/../kind-manifests"

source "${current_dir}/lib.sh"

while ! kubectl apply -k ${current_dir}
do
  echo "waiting for resource apply to succeed"
  sleep 10
done

create_minio_endpoint_route && create_bucket
delete_minio_endpoint_route

# kubectl port-forward -n minio-operator svc/minio 9445:443 # port-forward minio store
# mc alias set ai-demo https://localhost:9445 minio minio1234 --insecure # set a minio host alias
# kubectl port-forward -n minio-operator svc/minio-tenant-console 9444:9443 # port-forward tenant console (login with credentials in minio-storage-configuration.yaml)
# mc mb ai-demo/ai-demo --insecure # Create bucket 'ai-demo'

# mc admin config set ai-demo/ notify_webhook:PRIMARY endpoint="http://event-display.ai-demo.svc.cluster.local:80" --insecure # Setup webhook notification to endpoint
# mc admin service restart ai-demo/ --insecure # Required after a config change
# mc event add ai-demo/ai-demo arn:minio:sqs::PRIMARY:webhook --event put --insecure # Subscribe to PUT events

# mc admin config set ai-demo/ notify_webhook:minio-webhook-source endpoint="http://minio-webhook-source.ai-demo.svc.cluster.local:80" --insecure # Setup webhook notification to endpoint
# mc admin service restart ai-demo/ --insecure # Required after a config change
# mc event add ai-demo/ai-demo arn:minio:sqs::minio-webhook-source:webhook --event put --insecure # Subscribe to PUT events

# Upload some files for testing
# mc cp --recursive infra/openshift-manifests/ ai-demo/ai-demo --insecure

 # mc rm --recursive ai-demo/ai-demo  --dangerous --force --insecure # VERY DANGEROUS: remove every file in bucket