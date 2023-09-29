# Minio webhook source

This service:
 - gets feedbacks at `/feedbacks` and persist them to Postgresql for analytics

This image is published at `quay.io/kevent-mesh/ai-demo-analytics-service:main`.


# Sending feedbacks

```shell
kubectl get routes -n knative-serving-ingress # Get analytics service route URL
analytics_service_route_host="analytics-service-ai-demo.apps.<omitted>"
curl -X POST -H "Content-Type: application/json" http://${analytics_service_route_host}/feedbacks -d '{"feedback": 1, "uploadId": "xyz"}'
```


