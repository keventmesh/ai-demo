import asyncio


async def upload(image_path, upload_service_url):
    print(f"upload {image_path} to {upload_service_url}")
    await asyncio.sleep(0.05)
    # TODO: return upload_id
    pass


async def init_reply_ws_connection(reply_service_url):
    print(f"init reply ws connection to {reply_service_url}")
    # TODO: start a WS connection to reply service
    # TODO: return connection
    await asyncio.sleep(0.05)
    pass


async def wait_for_reply(conn, upload_id):
    print(f"wait for reply for {upload_id}")
    # ask for reply
    # return reply
    await asyncio.sleep(0.05)
    pass


async def send_feedback(upload_id, feedback, feedback_service_url):
    print(f"send feedback for {upload_id} to {feedback_service_url}")
    # TODO: send feedback, wait until it is successfully sent
    await asyncio.sleep(0.05)
    pass
