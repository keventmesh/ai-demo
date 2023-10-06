import asyncio
import base64
import uuid

import aiohttp
import socketio
import logging

DEFAULT_HTTP_REQUEST_TIMEOUT = 3600
DEFAULT_WS_CONNECTION_TIMEOUT=3600

logger = logging.getLogger(__name__)


async def upload(image_path, upload_service_url, fake):
    logger.debug(f"upload '{image_path}' to {upload_service_url}")

    if fake:
        await asyncio.sleep(0.1)
        return True, "fake_" + uuid.uuid4().hex

    with open(image_path, mode='rb') as file:
        image_binary = file.read()

    image_base64 = base64.b64encode(image_binary)
    image_base64 = image_base64.decode("utf-8")

    data = {
        "image_b64": image_base64
    }

    try:
        timeout = aiohttp.ClientTimeout(total=DEFAULT_HTTP_REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(upload_service_url, json=data) as response:
                if response.status >= 400:
                    # TODO message
                    raise Exception(f"Failed to upload image {image_path} to {upload_service_url}")

                response_json = await response.json()
                if not response_json:
                    raise Exception(f"Empty response body from {upload_service_url} for image {image_path}")
                if 'uploadId' not in response_json:
                    raise Exception(
                        f"Missing uploadId in response body from {upload_service_url} for image {image_path}")
                logger.debug(
                    f"Uploaded image {image_path} to {upload_service_url} with uploadId {response_json['uploadId']}")
                return True, response_json['uploadId']
    except Exception as e:
        logger.warning(f"Failed to upload image {image_path} to {upload_service_url}: {e}")
        logger.warning(e, exc_info=True)
        return False, str(e)


async def init_reply_ws_connection(reply_service_url, fake):
    logger.debug(f"init reply ws connection to {reply_service_url}")

    if fake:
        await asyncio.sleep(0.1)
        return True, {}

    # connector = aiohttp.TCPConnector(ssl=False)
    # http_session = aiohttp.ClientSession(connector=connector)
    # http_session.verify = False
    # sio = socketio.AsyncClient(http_session=http_session)
    try:
        sio = socketio.AsyncClient(request_timeout=DEFAULT_WS_CONNECTION_TIMEOUT, logger=logger.isEnabledFor(logging.DEBUG), engineio_logger=logger.isEnabledFor(logging.DEBUG))
        await sio.connect(reply_service_url, transports=['websocket'])
        return True, sio
    except Exception as e:
        logger.warning(f"Failed to connect to {reply_service_url}: {e}")
        logger.warning(e, exc_info=True)
        return False, str(e)


async def wait_for_reply(conn, upload_id, fake):
    if fake:
        await asyncio.sleep(0.1)
        return True, {"uploadId": "fake_" + uuid.uuid4().hex, "probability": 0.5, "x0": 0.1, "x1": 0.2, "y0": 0.3,
                      "y1": 0.4, "created_on": "2021-01-01T00:00:00.000Z"}

    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    def on_message(data):
        if data['uploadId'] != upload_id:
            logger.debug(f"received event with data {data} but uploadId {data['uploadId']} != {upload_id}")
            return
        fut.set_result(data)

    def on_connect():
        logger.debug(f"Connected to reply service. upload_id: {upload_id}")

    def on_connect_error(data):
        logger.debug(f"Connection error for upload_id {upload_id}: {data}")
        fut.set_exception(Exception(f"Connection error for upload_id {upload_id}: {data}"))

    def on_disconnect():
        logger.debug(f"Disconnected from reply service. upload_id: {upload_id}")

    conn.on('connect', on_connect)
    conn.on('disconnect', on_disconnect)
    conn.on('connect_error', on_connect_error)
    conn.on('reply', on_message)

    try:
        logger.debug(f"Request reply for {upload_id}")
        await conn.emit('request_prediction_reply', {'uploadId': upload_id})
    except Exception as e:
        logger.warning(f"Failed to request reply for {upload_id}: {e}")
        logger.warning(e, exc_info=True)
        return False, e

    try:
        logger.debug(f"Wait for reply for {upload_id}")
        reply = (await fut)
        logger.debug(f"Received reply for {upload_id}: {reply}")
        return True, reply
    except Exception as e:
        logger.warning(f"Failed to wait for reply for {upload_id}: {e}")
        logger.warning(e, exc_info=True)
        return False, str(e)


async def send_feedback(upload_id, feedback, feedback_service_url, fake):
    logger.debug(f"Send feedback for {upload_id} to {feedback_service_url}")

    if fake:
        await asyncio.sleep(0.1)
        return True, None

    data = {
        "uploadId": upload_id,
        "feedback": feedback,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=DEFAULT_HTTP_REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(feedback_service_url, json=data, ) as response:
                if response.status >= 400:
                    raise Exception(f"Failed to send feedback for {upload_id} to {feedback_service_url}")
        return True, None
    except Exception as e:
        logger.warning(f"Failed to send feedback for {upload_id} to {feedback_service_url}: {e}")
        logger.warning(e, exc_info=True)
        return False, str(e)


async def disconnect_ws(conn, fake):
    logger.debug(f"Disconnect from reply service")

    if fake:
        await asyncio.sleep(0.1)
        return True, None

    try:
        await conn.disconnect()
        return True, None
    except Exception as e:
        logger.warning(f"Failed to disconnect from reply service: {e}")
        logger.warning(e, exc_info=True)
        return False, str(e)
