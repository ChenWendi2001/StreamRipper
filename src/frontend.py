import pickle
import re
import threading
from enum import Enum
from queue import Queue

import mitmproxy.http

from Middleware.main import main_func
from Middleware.utils import changeRequest, extractResponse
from utils import printInfo, printWarn


class Status(Enum):
    OK = 1
    Error = 0


class Router:
    def __init__(self):
        printInfo("init Router")
        self.task_queue = Queue()
        self.done_queue = Queue()
        self.main_proc = threading.Thread(
            target=main_func, daemon=True,
            args=(self.task_queue, self.done_queue))
        self.main_proc.start()

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # only intercept GET requests
        request = flow.request
        self.from_db = False

        # check delegation
        scheduler_flag = request.headers.get(
            "scheduler", default="False")
        if scheduler_flag == "True":
            printInfo("\033[44m receive a delegation \033[0m")
            return

        # filter
        if request.method != "GET":
            printWarn(True, "status: Error")
            return

        # NOTE: request.method == "GET"
        status, key = self.get_key_from_request(request)
        if status == Status.OK:
            printInfo("status: OK")
            self.task_queue.put(("query", key, request))
            data = self.done_queue.get()
            printInfo(f"get data {data[:10]}")

            # NOTE: get data from db
            if not isinstance(data, tuple):
                printInfo("\033[42m frontend hit or partial hit \033[0m")
                response = pickle.loads(data)
                response.headers["Server"] = "StreamRipper"
                flow.response = response
                self.from_db = True
            else:
                printInfo("\033[47m frontend miss \033[0m")
                v_range, ori_range = data
                flow.request = changeRequest(
                    flow.request, *v_range, ori_range)

    def response(self, flow: mitmproxy.http.HTTPFlow):
        request = flow.request
        if request.method == "GET":
            status, key = self.get_key_from_request(request)
            if status == Status.OK \
                    and not self.from_db:
                self.task_queue.put(
                    ("insert", key, flow.response))
                start, end = map(
                    int, request.headers["ori-range"].split(","))
                flow.response = extractResponse(
                    flow.response, start, end)

    def http_connect(self, flow: mitmproxy.http.HTTPFlow):
        # for future use
        pass

    def get_key_from_request(self, request):
        # get file name
        path = request.path
        if path.find(".m4s") == -1:
            return Status.Error, None
        filename = path[:path.find(".m4s")].split("/")[-1].split("-")[-1]

        # request header (contains referer and range)
        headers = request.headers
        referer = headers.get(
            "referer", default="no referer")
        range = headers.get(
            "range", default="no range").lstrip("bytes=")

        # parse
        if referer != "no referer":
            referer = re.search("(BV\w+)", referer).group()

        status = Status(
            referer != "no referer" and range != "no range")

        return status, "-".join([referer, filename, range])


addons = [
    Router()
]
