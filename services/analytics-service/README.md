# Minio webhook source

This service:
 - gets feedbacks at `/feedbacks` and persist them to Postgresql for analytics

This image is published at `quay.io/kevent-mesh/ai-demo-analytics-service:main`.


# Sending feedbacks

```shell
analytics_service_url=$(k get ksvc -n ai-demo analytics-service -o=jsonpath='{.status.url}')
curl -v -X POST -H "Content-Type: application/json" ${analytics_service_url}/feedbacks -d '{"uploadId": "xyz", "feedback": 1}'
```

# Sending predictions

```shell
analytics_service_url=$(k get ksvc -n ai-demo analytics-service -o=jsonpath='{.status.url}')
curl -v -X POST -H "Content-Type: application/json" ${analytics_service_url}/predictions -d '{"uploadId": "xyz", "probability": 0.999, "x0": 0.24543, "x1": 0.24543, "y0": 0.24543, "y1": 0.24543}'
```


