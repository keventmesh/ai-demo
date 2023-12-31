#!/usr/bin/env bash

set -e pipefail

script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

function create_minio_client_config(){
    MINIO_ENDPOINT=$(oc get route -n minio-operator minio-endpoint -o jsonpath="{.status.ingress[0].host}")

    # create a temp directory on the host machine (your machine) to store the mc config
    rm -rf /tmp/mc-config
    mkdir /tmp/mc-config

    # execute operations with /tmp/mc-config mounted to the container's /mc-config directory
    #
    # set alias for our minio instance
    docker run --user "$(id -u):$(id -g)" --rm -v /tmp/mc-config:/mc-config minio/mc:edge --config-dir=/mc-config --insecure    alias set ai-demo "https://${MINIO_ENDPOINT}" minio minio1234
}

function delete_minio_client_config(){
  rm -rf /tmp/mc-config
}

function create_minio_endpoint_route() {
    # create a route for the minio service
    cat <<EOF | oc apply -f -
    kind: Route
    apiVersion: route.openshift.io/v1
    metadata:
      name: minio-endpoint
      namespace: minio-operator
    spec:
      to:
        kind: Service
        name: minio
        weight: 100
      port:
        targetPort: https-minio
      tls:
        termination: passthrough
        insecureEdgeTerminationPolicy: Redirect
EOF
}

function create_bucket() {
    # create a bucket
    docker run --rm --user "$(id -u):$(id -g)" -v /tmp/mc-config:/mc-config minio/mc:edge --config-dir=/mc-config --insecure    mb ai-demo/ai-demo --ignore-existing
}

function delete_minio_endpoint_route(){
    oc delete route -n minio-operator minio-endpoint
}

function add_minio_webhook(){
    # wait until minio-webhook-source Knative Service are ready
    oc wait --for=condition=Ready --timeout=20m ksvc -n ai-demo minio-webhook-source

    # get the internal address of the minio webhook service
    endpoint=$(oc get ksvc -n ai-demo minio-webhook-source -ojsonpath="{.status.address.url}")

    # set the webhook endpoint, which is our minio webhook source service
    docker run --user "$(id -u):$(id -g)" --rm -v /tmp/mc-config:/mc-config minio/mc:edge --config-dir=/mc-config --insecure    admin config set ai-demo/ notify_webhook:minio-webhook-source endpoint="${endpoint}:80"

    # restart the minio service
    docker run --user "$(id -u):$(id -g)" --rm -v /tmp/mc-config:/mc-config minio/mc:edge --config-dir=/mc-config --insecure    admin service restart ai-demo/

    # Subscribe to PUT events
    docker run --user "$(id -u):$(id -g)" --rm -v /tmp/mc-config:/mc-config minio/mc:edge --config-dir=/mc-config --insecure    event add ai-demo/ai-demo arn:minio:sqs::minio-webhook-source:webhook --event put --ignore-existing
}

function patch_knative_serving(){
    # patch knative serving to use http instead of https in the service status url
    oc patch knativeserving -n knative-serving knative-serving -p '{"spec":{"config":{"network":{"default-external-scheme": "http"}}}}' --type=merge

    # patch knative serving to only keep one revision of a service
    kubectl patch configmap/config-gc \
        -n knative-serving \
        --type merge \
        -p '{"data":{"min-non-active-revisions":"0", "max-non-active-revisions":"0"}}'

    # wait until knative serving is ready
    oc wait --for=condition=Ready knativeserving --timeout=20m -n knative-serving knative-serving
}

function patch_ui_service_configmap(){
    # wait until services are ready
    oc wait --for=condition=Ready ksvc -n ai-demo --timeout=20m upload-service
    oc wait --for=condition=Ready ksvc -n ai-demo --timeout=20m feedback-service
    # it is not easy to wait for a route
    # oc wait --for=... route -n ai-demo reply-service

    uploadServiceUrl=$(oc get ksvc -n ai-demo upload-service -o jsonpath="{.status.url}")
    echo "uploadServiceUrl: ${uploadServiceUrl}"

    replyServiceUrl=$(oc get route -n ai-demo reply-service -o jsonpath="{.spec.host}")
    replyServiceUrl="http://${replyServiceUrl}"
    echo "replyServiceUrl: ${replyServiceUrl}"

    feedbackServiceUrl=$(oc get ksvc -n ai-demo feedback-service -o jsonpath="{.status.url}")
    echo "feedbackServiceUrl: ${feedbackServiceUrl}"

    # patch the ui service configmap with the service urls
    oc patch configmap -n ai-demo ui-service --patch "{\"data\": {\"upload-service-url\": \"${uploadServiceUrl}\"}}"
    oc patch configmap -n ai-demo ui-service --patch "{\"data\": {\"reply-service-url\": \"${replyServiceUrl}\"}}"
    oc patch configmap -n ai-demo ui-service --patch "{\"data\": {\"feedback-service-url\": \"${feedbackServiceUrl}\"}}"

    # touch the ksvc so that it is redeployed with the new configmap
    oc patch ksvc -n ai-demo ui-service --type=json -p='[{"op": "replace", "path": "/spec/template/metadata/annotations", "value": {"dummy": '"\"$(date '+%Y%m%d%H%M%S')\""'}}]'

}

function install_postgresql() {
  oc process -n openshift postgresql-persistent -p POSTGRESQL_DATABASE=ai-demo -p VOLUME_CAPACITY=2Gi -p POSTGRESQL_USER=ai-demo -p POSTGRESQL_PASSWORD=ai-demo | oc apply -n ai-demo -f - || return $?
}

function install_grafana_dashboard() {
  oc wait --for=condition=Ready ksvc -n ai-demo --timeout=20m admin-service
  admin_service_url=$(oc get ksvc -n ai-demo admin-service -o jsonpath="{.status.url}")

  export ADMIN_SERVICE_URL=$admin_service_url

  kubectl create configmap grafana-admin-dashboard -n grafana --from-file="${script_dir}/analytics-service/grafana-admin-dashboard.json" --dry-run=client -oyaml | envsubst '${ADMIN_SERVICE_URL}' | kubectl apply -f -
}
