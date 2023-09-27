import os
import signal
import sys

from flask import Flask, render_template
from flask_cors import CORS, cross_origin

MAX_IMG_WIDTH = int(os.environ.get("MAX_IMG_WIDTH", 640))
MAX_IMG_HEIGHT = int(os.environ.get("MAX_IMG_HEIGHT", 640))

UPLOAD_SERVICE_URL = os.environ.get("UPLOAD_SERVICE_URL")
REPLY_SERVICE_URL = os.environ.get("REPLY_SERVICE_URL")

if not UPLOAD_SERVICE_URL:
    raise Exception("Missing UPLOAD_SERVICE_URL")
if not REPLY_SERVICE_URL:
    raise Exception("Missing REPLY_SERVICE_URL")

print("UPLOAD_SERVICE_URL: ", UPLOAD_SERVICE_URL)
print("REPLY_SERVICE_URL: ", REPLY_SERVICE_URL)
print("MAX_IMG_WIDTH: ", MAX_IMG_WIDTH)
print("MAX_IMG_HEIGHT: ", MAX_IMG_HEIGHT)

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

def handler(signal, frame):
    print('Gracefully shutting down')
    sys.exit(0)


signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)


@app.get('/')
@cross_origin()
def send_client_html():
    return render_template('index.html',
                           max_img_width=MAX_IMG_WIDTH,
                           max_img_height=MAX_IMG_HEIGHT,
                           upload_service_url=UPLOAD_SERVICE_URL,
                           reply_service_url=REPLY_SERVICE_URL
                           )


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
