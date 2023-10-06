import asyncio
import json
import time

from lib import upload, send_feedback, wait_for_reply, init_reply_ws_connection


class Span:
    def __init__(self, name, parent=None):
        self.name = name
        self.start_time = time.time()
        self.end_time = None
        self.children = []
        self.parent = parent

    def start(self, name):
        s = Span(name, self)
        s.start_time = time.time()
        self.children.append(s)
        return s

    def end(self):
        self.end_time = time.time()
        return self.parent

    def print(self, indent=0):
        print(f"{' ' * indent}{self.name}: {self.end_time - self.start_time}")
        for child in self.children:
            child.print(indent + 2)

    def build_summary(self):
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
    def __init__(self, image_data_list, image_index, upload_service_url, feedback_service_url, reply_service_url):
        self.image_data_list = image_data_list
        self.image_index = image_index
        self.upload_service_url = upload_service_url
        self.feedback_service_url = feedback_service_url
        self.reply_service_url = reply_service_url

    async def start(self, span, http_req_semaphore, ws_req_semaphore):
        s = span.start("client")

        image_data = self.image_data_list[self.image_index]
        image_path = image_data['image']
        feedback = image_data['feedback']

        s = s.start("init_ws_connection")
        async with ws_req_semaphore:
            s = s.start("do_init_ws_connection")
            ok, ws_conn = await init_reply_ws_connection(self.reply_service_url)
            if not ok:
                print(f"Failed to init ws connection, killing client")
                s.end().end()
                return
            s = s.end()
        s = s.end()

        s = s.start("upload")
        async with http_req_semaphore:
            s = s.start("send_upload_request")
            ok, upload_id = await upload(image_path, self.upload_service_url)
            if not ok:
                print(f"Failed to upload {image_path}, killing client")
                s.end().end()
                return
            s = s.end()
        s = s.end()

        s = s.start("reply")
        async with ws_req_semaphore:
            s = s.start("wait_for_reply")
            ok, _ = await wait_for_reply(ws_conn, upload_id)
            if not ok:
                print(f"Failed to wait for reply for {upload_id}, killing client")
                s.end().end()
                return
            try:
                await ws_conn.disconnect()
            except Exception as e:
                print(f"Failed to disconnect from reply service: {e}, killing client")
                s.end().end()
                return

            s = s.end()
        s = s.end()

        s = s.start("feedback")
        async with http_req_semaphore:
            s = s.start("send_feedback_request")
            ok, _ = await send_feedback(upload_id, feedback, self.feedback_service_url)
            if not ok:
                print(f"Failed to send feedback for {upload_id}, killing client")
                s.end().end()
                return
            s = s.end()
        s = s.end()

        # end the "client" span
        s.end()


async def runPass(total_client_count, concurrent_client_count, max_concurrent_ws_requests, max_concurrent_http_requests,
                  upload_service, feedback_service, reply_service, input_file):
    with open(input_file) as f:
        image_data_list = json.load(f)

    print(f"There are {len(image_data_list)} images in the input file.")

    clients = []
    for i in range(total_client_count):
        clients.append(
            Client(image_data_list, i % len(image_data_list), upload_service, feedback_service, reply_service))

    http_req_semaphore = asyncio.Semaphore(max_concurrent_http_requests)
    ws_req_semaphore = asyncio.Semaphore(max_concurrent_ws_requests)

    client_sem = asyncio.Semaphore(concurrent_client_count)

    root_span = Span("root")

    async def start_client(cl):
        async with client_sem:
            await cl.start(root_span, http_req_semaphore, ws_req_semaphore)

    async with asyncio.TaskGroup() as tg:
        for client in clients:
            tg.create_task(start_client(client))

    root_span.end()

    # print root span time
    print(f"Total time: {root_span.end_time - root_span.start_time}")

    span_summary = root_span.build_summary()
    for span_name, durations in span_summary.items():
        print(
            f"{span_name:<80} ({len(durations):>5} executions) with average {sum(durations) / len(durations):.4f} seconds")


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
    # args = parser.parse_args()

    args = {
        'total_client_count': 5,
        'concurrent_client_count': 50,
        'max_concurrent_http_requests': 100,
        'max_concurrent_ws_requests': 100,
        'upload_service': 'http://upload-service-ai-demo.apps.aliok-c145.serverless.devcluster.openshift.com',
        'feedback_service': 'http://feedback-service-ai-demo.apps.aliok-c145.serverless.devcluster.openshift.com',
        'reply_service': 'http://reply-service-ai-demo.apps.aliok-c145.serverless.devcluster.openshift.com',
        'input': 'data.json'
    }

    class FakeArgs:
        def __init__(self, args):
            self.__dict__.update(args)

    args = FakeArgs(args)

    print(args.__dict__)

    await runPass(args.total_client_count, args.concurrent_client_count,
                  args.max_concurrent_ws_requests, args.max_concurrent_http_requests,
                  args.upload_service, args.feedback_service, args.reply_service,
                  args.input)


if __name__ == '__main__':
    asyncio.run(main())
