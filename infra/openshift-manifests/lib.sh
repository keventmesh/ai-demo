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
