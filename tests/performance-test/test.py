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
            ws_conn = await init_reply_ws_connection(self.upload_service_url)
            s = s.end()
        s = s.end()

        s = s.start("upload")
        async with http_req_semaphore:
            s = s.start("send_upload_request")
            upload_id = await upload(image_path, self.upload_service_url)
            s = s.end()
        s = s.end()

        s = s.start("reply")
        async with ws_req_semaphore:
            s = s.start("wait_for_reply")
            await wait_for_reply(ws_conn, upload_id)
            s = s.end()
        s = s.end()

        s = s.start("feedback")
        async with http_req_semaphore:
            s = s.start("send_feedback_request")
            await send_feedback(upload_id, feedback, self.feedback_service_url)
            s = s.end()
        s = s.end()

        # end the "client" span
        s.end()


async def runPass(totalClientCount, concurrentClientCount, maxConcurrentWsRequests, maxConcurrentHttpRequests,
                  uploadService,
                  feedbackService, replyService, input):
    print(f"totalClientCount: {totalClientCount}")
    print(f"concurrentClientCount: {concurrentClientCount}")
    print(f"maxConcurrentHttpRequests: {maxConcurrentHttpRequests}")
    print(f"maxConcurrentWsRequests: {maxConcurrentWsRequests}")
    print(f"uploadService: {uploadService}")
    print(f"feedbackService: {feedbackService}")
    print(f"replyService: {replyService}")
    print(f"input: {input}")

    with open(input) as f:
        image_data_list = json.load(f)

    print(f"There are {len(image_data_list)} images in the input file.")

    clients = []
    for i in range(totalClientCount):
        clients.append(Client(image_data_list, i % len(image_data_list), uploadService, feedbackService, replyService))

    http_req_semaphore = asyncio.Semaphore(maxConcurrentHttpRequests)
    ws_req_semaphore = asyncio.Semaphore(maxConcurrentWsRequests)

    client_sem = asyncio.Semaphore(concurrentClientCount)

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
        print(f"{span_name:<80} ({len(durations):>5} executions) with average {sum(durations) / len(durations):.4f} seconds")


async def main():
    # params:
    #   --total-clients:                  number of total clients
    #   --concurrent-clients:             number of concurrent clients
    #   --max-concurrent-http-requests:   max number of concurrent HTTP requests (upload+feedback) in total for all clients
    #   --max-concurrent-ws-requests:     max number of concurrent WS requests (reply) in total for all clients
    #   --upload-service:                 upload service url
    #   --feedback-service:               feedback service url
    #   --reply-service:                  reply service url
    #   --input:                          input JSON file

    totalClientCount = 10
    concurrentClientCount = 2
    maxConcurrentHttpRequests = 20
    maxConcurrentWsRequests = 20
    uploadService = 'http://localhost:8080/upload'
    feedbackService = 'http://localhost:8080/feedback'
    replyService = 'ws://localhost:8080/reply'
    input = 'data.json'

    await runPass(totalClientCount, concurrentClientCount, maxConcurrentWsRequests,
                  maxConcurrentHttpRequests, uploadService, feedbackService, replyService, input)


if __name__ == '__main__':
    asyncio.run(main())
