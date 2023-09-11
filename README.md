
Order of things:

1. [training](training)
  - Train the model
  - Export it
2. [inference_test](inference_test)
  - Sanity check the exported model
  - Plot the detections onto test images
3. [tensorflow_serving_test](tensorflow_serving_test)
  - Use the exported model in a TensorFlow Serving container
  - Send inference requests to the container
    - Prepare input
    - Process output
4. [kserve_test](kserve_test)
  - Use the exported model in KServe
  - Send inference requests to the KServe InferenceService
    - Prepare input
    - Process output
5. [prediction_backend](prediction_backend)
  - Use the exported model in a Flask app
  - Send inference requests to the Flask app from a HTML page


TODO:
- Inference with KServe takes too long and needs too much CPU
  - Inference using a 100x83 image takes 1.5s with 5 CPU and 12Gi memory
  - Inference using a 960x540 image takes ~4.5s with 5 CPU and 12Gi memory
  - Inference using a 6000x8000 image (image to be posted by a phone) takes ~100s with 5 CPU and 12Gi memory
  - When CPU is set to 1, durations are ~2.5x longer
  - When TensorFlow Serving is used in a Docker container, durations are much shorter (no memory/CPU limit)
- Use secrets for credentials in general

TODO:
- Use Gunicorn for production (containers) (https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xix-deployment-on-docker-containers)
- 
