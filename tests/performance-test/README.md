## Development environment setup
Setup virtual environment:
```shell
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```shell
pip install -r requirements.txt
```

## Scale down images
```shell
python scale.py
```

This will take images from `images/source` folder and scale them down to 640x640 and save them to `images/scaled` folder.

## Filling the image data file
```shell
python fill_image_data.py
```

This will take images from `images/scaled` folder and create `image_data.json` file with image data.
It will preserve any feedback specified for the image. If there is no feedback for the image, a random feedback will be generated.

## Running the performance test:

```shell
> python test.py

usage: test.py [-h] --total-clients TOTAL_CLIENTS --concurrent-clients CONCURRENT_CLIENTS --max-concurrent-http-requests MAX_CONCURRENT_HTTP_REQUESTS --max-concurrent-ws-requests MAX_CONCURRENT_WS_REQUESTS --upload-service UPLOAD_SERVICE --feedback-service FEEDBACK_SERVICE --reply-service REPLY_SERVICE ─╯
               --input INPUT [--verbose] [--fake] [--regular-report]

options:
  -h, --help            show this help message and exit
  --total-clients TOTAL_CLIENTS
                        number of total clients
  --concurrent-clients CONCURRENT_CLIENTS
                        number of concurrent clients
  --max-concurrent-http-requests MAX_CONCURRENT_HTTP_REQUESTS
                        max number of concurrent HTTP requests (upload+feedback) in total for all clients
  --max-concurrent-ws-requests MAX_CONCURRENT_WS_REQUESTS
                        max number of concurrent WS requests (reply) in total for all clients
  --upload-service UPLOAD_SERVICE
                        upload service url
  --feedback-service FEEDBACK_SERVICE
                        feedback service url
  --reply-service REPLY_SERVICE
                        reply service url
  --input INPUT         input JSON file
  --verbose             Enable verbose logging
  --fake                Do not actually call any services, just sleep
  --regular-report      Report progress every 5 seconds
```

Your typical workflow:
```shell
uploadServiceUrl=$(oc get ksvc -n ai-demo upload-service -o jsonpath="{.status.url}")
echo "uploadServiceUrl: ${uploadServiceUrl}"

replyServiceUrl=$(oc get route -n ai-demo reply-service -o jsonpath="{.spec.host}")
replyServiceUrl="http://${replyServiceUrl}"
echo "replyServiceUrl: ${replyServiceUrl}"

feedbackServiceUrl=$(oc get ksvc -n ai-demo feedback-service -o jsonpath="{.status.url}")
echo "feedbackServiceUrl: ${feedbackServiceUrl}"

python test.py \
    --total-clients=100 \
    --concurrent-clients=50 \
    --max-concurrent-http-requests=500 \
    --max-concurrent-ws-requests=500 \
    --upload-service="${uploadServiceUrl}" \
    --feedback-service="${feedbackServiceUrl}" \
    --reply-service="${replyServiceUrl}" \
    --input=data.json \
    --regular-report
```

Output:
```shell
INFO:__main__:-----------------Done!------------------------------------------
INFO:__main__:---------Span summary for finished spans:---------
INFO:__main__:	root                                                                             (    1 executions) with average 66.9122 seconds
INFO:__main__:	root->client                                                                     (  100 executions) with average 15.5505 seconds
INFO:__main__:	root->client->init_ws_connection                                                 (  100 executions) with average 0.6220 seconds
INFO:__main__:	root->client->init_ws_connection->do_init_ws_connection                          (  100 executions) with average 0.6220 seconds
INFO:__main__:	root->client->upload                                                             (  100 executions) with average 2.9328 seconds
INFO:__main__:	root->client->upload->send_upload_request                                        (  100 executions) with average 2.9328 seconds
INFO:__main__:	root->client->reply                                                              (  100 executions) with average 11.5201 seconds
INFO:__main__:	root->client->reply->wait_for_reply                                              (  100 executions) with average 11.5201 seconds
INFO:__main__:	root->client->feedback                                                           (   97 executions) with average 0.4902 seconds
INFO:__main__:	root->client->feedback->send_feedback_request                                    (   97 executions) with average 0.4902 seconds
INFO:__main__:---------Task summary of tasks so far:---------
INFO:__main__:Done: 100, In progress: 0, Total: 100
INFO:__main__:	ok: 97
INFO:__main__:	wait_for_reply: 3
```

This means:
- 100 clients were created
- 97 clients finished successfully
- 3 clients failed when waiting for reply

Times:
- Clients were running for 15.5505 seconds on average
- Uploading the image took 2.9328 seconds on average
- Waiting for reply took 11.5201 seconds on average
- Sending feedback took 0.4902 seconds on average
