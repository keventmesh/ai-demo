#!/usr/bin/env bash

current_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
manifests_dir="${current_dir}/../kind-manifests"

source "${current_dir}/lib.sh"

export DOCKER_REPO_OVERRIDE="${DOCKER_REPO_OVERRIDE:-"quay.io/kevent-mesh"}"
export AI_DEMO_IMAGE_TAG="${AI_DEMO_IMAGE_TAG:-main}"

while ! kustomize build "${current_dir}" | envsubst | kubectl apply -f -;
do
  echo "waiting for resource apply to succeed"
  sleep 10
done

install_grafana_dashboard

patch_knative_serving

create_minio_endpoint_route && create_minio_client_config && create_bucket && add_minio_webhook
delete_minio_endpoint_route
delete_minio_client_config

patch_ui_service_configmap

install_postgresql

# kubectl port-forward svc/grafana-service -n grafana 3000:3000 # Port-forward grafana

# kubectl run -it -n ai-demo --image=postgres --env="POSTGRES_PASSWORD=ai-demo" --env="PGPASSWORD=ai-demo" psql -- psql --host=postgresql.ai-demo.svc --port=5432 --username=ai-demo # connect to postgresql server

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

### Testing webhook
# source ./lib.sh
# create_minio_endpoint_route && create_minio_client_config
#
# docker run -v /tmp/mc-config:/mc-config minio/mc:edge --config-dir=/mc-config --insecure    admin config get ai-demo/ notify_webhook
# docker run -v /tmp/mc-config:/mc-config minio/mc:edge --config-dir=/mc-config --insecure    admin config get ai-demo/ai-demo notify_webhook
# docker run -v /tmp/mc-config:/mc-config minio/mc:edge --config-dir=/mc-config --insecure    cp --recursive /mc-config ai-demo/ai-demo
#
# delete_minio_endpoint_route
