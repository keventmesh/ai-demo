import asyncio
import json
import logging
import time

from lib import upload, send_feedback, wait_for_reply, init_reply_ws_connection, disconnect_ws

logger = logging.getLogger(__name__)


class Span:
    def __init__(self, name, parent=None):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.children = []
        self.parent = parent

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        if exc_val is not None:
            logger.warning(f"Exception in span {self.name}: {exc_val}")
            logger.exception(exc_tb)
            # logger.warning(exc_tb.format_exc())
        return True

    def subspan(self, name):
        s = Span(name, self)
        self.children.append(s)
        return s

    def print(self, indent=0):
        print(f"{' ' * indent}{self.name}: {self.end_time - self.start_time}")
        for child in self.children:
            child.print(indent + 2)

    def build_summary(self):
        if self.end_time is None:
            # name -> [duration]
            summary = {
                self.name: []
            }
        else:
            # name -> [duration]
            summary = {
                self.name: [self.end_time - self.start_time]
            }

        if len(self.children) != 0:
            for child in self.children:
                child_summary = child.build_summary()
                for child_name, child_durations in child_summary.items():
                    child_full_name = f"{self.name}->{child_name}"
                    if child_full_name not in summary:
                        summary[child_full_name] = []
                    summary[child_full_name].extend(child_durations)
        return summary


class Client:
    def __init__(self, image_data_list, image_index, upload_service_url, feedback_service_url, reply_service_url, fake):
        self.image_data_list = image_data_list
        self.image_index = image_index
        self.upload_service_url = upload_service_url
        self.feedback_service_url = feedback_service_url
        self.reply_service_url = reply_service_url
        self.fake = fake

    async def start(self, root_span, http_req_semaphore, ws_req_semaphore):
        image_data = self.image_data_list[self.image_index]
        image_path = image_data['image']
        feedback = image_data['feedback']

        with root_span.subspan("client") as client_span:

            with client_span.subspan("init_ws_connection") as init_ws_connection_span:
                async with ws_req_semaphore:
                    with init_ws_connection_span.subspan("do_init_ws_connection"):
                        ok, ws_conn = await init_reply_ws_connection(self.reply_service_url, self.fake)
                        if not ok:
                            logger.warning(f"Failed to init ws connection, stopping processing with client")
                            return

            with client_span.subspan("upload") as upload_span:
                async with http_req_semaphore:
                    with upload_span.subspan("send_upload_request"):
                        ok, upload_id = await upload(image_path, self.upload_service_url, self.fake)
                        if not ok:
                            logger.warning(f"Failed to upload {image_path}, stopping processing with client")
                            return

            with client_span.subspan("reply") as reply_span:
                async with ws_req_semaphore:
                    with reply_span.subspan("wait_for_reply"):
                        ok, _ = await wait_for_reply(ws_conn, upload_id, self.fake)
                        if not ok:
                            logger.warning(f"Failed to wait for reply for {upload_id}, stopping processing with client")
                            return
                        ok, _ = await disconnect_ws(ws_conn, self.fake)
                        if not ok:
                            logger.warning(
                                f"Failed to disconnect from reply servicefor {upload_id} , stopping processing with client")
                            return

            with client_span.subspan("feedback") as feedback_span:
                async with http_req_semaphore:
                    with feedback_span.subspan("send_feedback_request"):
                        ok, _ = await send_feedback(upload_id, feedback, self.feedback_service_url, self.fake)
                        if not ok:
                            logger.warning(f"Failed to send feedback for {upload_id}, stopping processing with client")
                            return


async def report(tg, root_span):
    await asyncio.sleep(5)
    in_progress_client_count = len(tg._tasks) - 1  # exclude this report task
    loop = asyncio.get_running_loop()
    scheduled_async_calls = len(loop._scheduled)
    if in_progress_client_count > 0:
        logger.info(
            f"In progress client count: {in_progress_client_count}, scheduled_async_calls: {scheduled_async_calls}")

        logger.info("Span summary for finished spans:")
        span_summary = root_span.build_summary()
        for span_name, durations in span_summary.items():
            avg = sum(durations) / len(durations) if len(durations) > 0 else 0
            logger.info(
                f"\t{span_name:<80} ({len(durations):>5} executions) with average {avg:.4f} seconds")

        tg.create_task(report(tg, root_span))


async def runPass(total_client_count, concurrent_client_count, max_concurrent_ws_requests, max_concurrent_http_requests,
                  upload_service, feedback_service, reply_service, input_file, fake):
    with open(input_file) as f:
        image_data_list = json.load(f)

    logger.info(f"There are {len(image_data_list)} images in the input file.")

    clients = []
    for i in range(total_client_count):
        clients.append(
            Client(image_data_list, i % len(image_data_list), upload_service, feedback_service, reply_service, fake))

    http_req_semaphore = asyncio.Semaphore(max_concurrent_http_requests)
    ws_req_semaphore = asyncio.Semaphore(max_concurrent_ws_requests)

    client_sem = asyncio.Semaphore(concurrent_client_count)

    with Span("root") as root_span:
        async def start_client(cl):
            async with client_sem:
                await cl.start(root_span, http_req_semaphore, ws_req_semaphore)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(report(tg, root_span))

            for client in clients:
                tg.create_task(start_client(client))


async def main():
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--total-clients', type=int, required=True, help='number of total clients')
    # parser.add_argument('--concurrent-clients', type=int, required=True, help='number of concurrent clients')
    # parser.add_argument('--max-concurrent-http-requests', type=int, required=True,
    #                     help='max number of concurrent HTTP requests (upload+feedback) in total for all clients')
    # parser.add_argument('--max-concurrent-ws-requests', type=int, required=True,
    #                     help='max number of concurrent WS requests (reply) in total for all clients')
    # parser.add_argument('--upload-service', type=str, required=True, help='upload service url')
    # parser.add_argument('--feedback-service', type=str, required=True, help='feedback service url')
    # parser.add_argument('--reply-service', type=str, required=True, help='reply service url')
    # parser.add_argument('--input', type=str, required=True, help='input JSON file')
    # parser.add_argument('--verbose', type=str, help='Enable verbose logging')
    # parser.add_argument('--fake', type=str, help='Don't actually call any services, just sleep')
    # args = parser.parse_args()

    args = {
        'total_client_count': 500,
        'concurrent_client_count': 100,
        'max_concurrent_http_requests': 100,
        'max_concurrent_ws_requests': 100,
        'upload_service': 'http://upload-service-ai-demo.apps.aliok-c147.serverless.devcluster.openshift.com',
        'feedback_service': 'http://feedback-service-ai-demo.apps.aliok-c147.serverless.devcluster.openshift.com',
        'reply_service': 'http://reply-service-ai-demo.apps.aliok-c147.serverless.devcluster.openshift.com',
        'input': 'data.json',
        # 'verbose': True,
        'verbose': False,
        # 'fake': True,
        'fake': False,
    }

    class FakeArgs:
        def __init__(self, args):
            self.__dict__.update(args)

    args = FakeArgs(args)

    logger.info(args.__dict__)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    await runPass(args.total_client_count, args.concurrent_client_count,
                  args.max_concurrent_ws_requests, args.max_concurrent_http_requests,
                  args.upload_service, args.feedback_service, args.reply_service,
                  args.input, args.fake)


if __name__ == '__main__':
    asyncio.run(main())