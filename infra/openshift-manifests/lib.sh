#!/usr/bin/env bash

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
    # Get the MinIO endpoint
    MINIO_ENDPOINT=$(oc get route -n minio-operator minio-endpoint -o jsonpath="{.status.ingress[0].host}")

    pip install boto3
    # Create a bucket named "ai-demo"
    python - <<EOF
import boto3
s3 = boto3.resource('s3', endpoint_url='https://${MINIO_ENDPOINT}', aws_access_key_id='minio', aws_secret_access_key='minio1234', verify=False)
s3.create_bucket(Bucket="ai-demo")
EOF

    if [ $? -eq 0 ]
    then
        echo "Created bucket"
    else
        echo "Error creating bucket"
        return 1
    fi
}

function delete_minio_endpoint_route(){
    oc delete route -n minio-operator minio-endpoint
}

function patch_knative_serving(){
    # patch knative serving to use http instead of https in the service status url
    oc patch knativeserving -n knative-serving knative-serving -p '{"spec":{"config":{"network":{"default-external-scheme": "http"}}}}' --type=merge
    # wait until knative serving is ready
    oc wait --for=condition=Ready knativeserving -n knative-serving knative-serving
}

function patch_ui_service_configmap(){
    # wait until services are ready
    oc wait --for=condition=Ready ksvc -n ai-demo upload-service
    # it is not easy to wait for a route
    # oc wait --for=... route -n ai-demo reply-service

    uploadServiceUrl=$(oc get ksvc -n ai-demo upload-service -o jsonpath="{.status.url}")
    echo "uploadServiceUrl: ${uploadServiceUrl}"

    replyServiceUrl=$(oc get route -n ai-demo reply-service -o jsonpath="{.spec.host}")
    replyServiceUrl="http://${replyServiceUrl}"
    echo "uploadServiceUrl: ${replyServiceUrl}"

    # patch the ui service configmap with the service urls
    oc patch configmap -n ai-demo ui-service --patch "{\"data\": {\"upload-service-url\": \"${uploadServiceUrl}\"}}"
    oc patch configmap -n ai-demo ui-service --patch "{\"data\": {\"reply-service-url\": \"${replyServiceUrl}\"}}"

    # touch the ksvc so that it is redeployed with the new configmap
    oc patch ksvc -n ai-demo ui-service --type=json -p='[{"op": "replace", "path": "/spec/template/metadata/annotations", "value": {"dummy": '"\"$(date '+%Y%m%d%H%M%S')\""'}}]'

}

install_postgresql() {
  oc process -n openshift postgresql-persistent -p POSTGRESQL_DATABASE=ai-demo -p VOLUME_CAPACITY=2Gi -p POSTGRESQL_USER=ai-demo -p POSTGRESQL_PASSWORD=ai-demo | oc apply -n ai-demo -f - || return $?
}
