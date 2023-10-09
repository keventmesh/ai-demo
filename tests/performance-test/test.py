import argparse
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

        try:
            with root_span.subspan("client") as client_span:

                with client_span.subspan("init_ws_connection") as init_ws_connection_span:
                    async with ws_req_semaphore:
                        with init_ws_connection_span.subspan("do_init_ws_connection"):
                            ok, ws_conn = await init_reply_ws_connection(self.reply_service_url, self.fake)
                            if not ok:
                                logger.warning(f"Failed to init ws connection, stopping processing with client")
                                return "init_ws_connection"

                with client_span.subspan("upload") as upload_span:
                    async with http_req_semaphore:
                        with upload_span.subspan("send_upload_request"):
                            ok, upload_id = await upload(image_path, self.upload_service_url, self.fake)
                            if not ok:
                                logger.warning(f"Failed to upload {image_path}, stopping processing with client")
                                return "upload"

                with client_span.subspan("reply") as reply_span:
                    async with ws_req_semaphore:
                        with reply_span.subspan("wait_for_reply"):
                            ok, _ = await wait_for_reply(ws_conn, upload_id, self.fake)
                            if not ok:
                                logger.warning(f"Failed to wait for reply for {upload_id}, stopping processing with client")
                                return "wait_for_reply"

                        with reply_span.subspan("disconnect"):
                            ok, _ = await disconnect_ws(ws_conn, self.fake)
                            if not ok:
                                logger.warning(
                                    f"Failed to disconnect from reply service for {upload_id} , stopping processing with client")
                                return "disconnect_ws"

                with client_span.subspan("feedback") as feedback_span:
                    async with http_req_semaphore:
                        with feedback_span.subspan("send_feedback_request"):
                            ok, _ = await send_feedback(upload_id, feedback, self.feedback_service_url, self.fake)
                            if not ok:
                                logger.warning(f"Failed to send feedback for {upload_id}, stopping processing with client")
                                return "feedback"

            return "ok"
        except Exception as e:
            logger.warning(f"Exception in client: {e}")
            logger.warning(e, exc_info=True)
            return "client"

def report_span(root_span):
    logger.info("---------Span summary for finished spans:---------")
    span_summary = root_span.build_summary()
    for span_name, durations in span_summary.items():
        avg = sum(durations) / len(durations) if len(durations) > 0 else 0
        logger.info(
            f"\t{span_name:<80} ({len(durations):>5} executions) with average {avg:.4f} seconds")
    print("------------------\n\n\n\n")


def report_tasks(tasks):
    output_for_finished = []  # List[str]
    for task in tasks:
        if task.done():
            output_for_finished.append(task.result())

    failure_reasons = {}
    for reason in output_for_finished:
        if reason not in failure_reasons:
            failure_reasons[reason] = 0
        failure_reasons[reason] += 1

    logger.info("---------Task summary of tasks so far:---------")
    logger.info(
        f"Done: {len(output_for_finished)}, In progress: {len(tasks) - len(output_for_finished)}, Total: {len(tasks)}")
    for reason, count in failure_reasons.items():
        logger.info(f"\t{reason}: {count}")


async def report(tg, root_span, tasks):
   try:
       await asyncio.sleep(5)
       in_progress_client_count = len(tg._tasks) - 1  # exclude this report task
       loop = asyncio.get_running_loop()
       scheduled_async_calls = len(loop._scheduled)
       if in_progress_client_count > 0:
           logger.info(
               f"In progress client count: {in_progress_client_count}, scheduled_async_calls: {scheduled_async_calls}")

           report_span(root_span)
           report_tasks(tasks)

           tg.create_task(report(tg, root_span, tasks))
   except Exception as e:
     logger.warning(f"Exception in report: {e}")
     logger.warning(e, exc_info=True)


async def runPass(total_client_count, concurrent_client_count, max_concurrent_ws_requests, max_concurrent_http_requests,
                  upload_service, feedback_service, reply_service, input_file, fake, regular_report):
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
                try:
                    return await cl.start(root_span, http_req_semaphore, ws_req_semaphore)
                except Exception as e:
                    logger.warning(f"Exception in client: {e}")
                    logger.warning(e, exc_info=True)
                    return "client_wrapper"

        tasks = []

        async with asyncio.TaskGroup() as tg:
            if regular_report:
                tg.create_task(report(tg, root_span, tasks))

            for client in clients:
                task = tg.create_task(start_client(client))
                tasks.append(task)

    logger.info("-----------------Done!------------------------------------------")
    report_span(root_span)
    report_tasks(tasks)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--total-clients', type=int, required=True, help='number of total clients')
    parser.add_argument('--concurrent-clients', type=int, required=True, help='number of concurrent clients')
    parser.add_argument('--max-concurrent-http-requests', type=int, required=True,
                        help='max number of concurrent HTTP requests (upload+feedback) in total for all clients')
    parser.add_argument('--max-concurrent-ws-requests', type=int, required=True,
                        help='max number of concurrent WS requests (reply) in total for all clients')
    parser.add_argument('--upload-service', type=str, required=True, help='upload service url')
    parser.add_argument('--feedback-service', type=str, required=True, help='feedback service url')
    parser.add_argument('--reply-service', type=str, required=True, help='reply service url')
    parser.add_argument('--input', type=str, required=True, help='input JSON file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--fake', action='store_true', help='Do not actually call any services, just sleep')
    parser.add_argument('--regular-report', action='store_true', help='Report progress every 5 seconds')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.DEBUG,
            datefmt='%Y-%m-%d %H:%M:%S')
    else:
        logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S')

    logger.info(args.__dict__)

    await runPass(args.total_clients, args.concurrent_clients,
                  args.max_concurrent_ws_requests, args.max_concurrent_http_requests,
                  args.upload_service, args.feedback_service, args.reply_service,
                  args.input, args.fake, args.regular_report)


if __name__ == '__main__':
    asyncio.run(main())
