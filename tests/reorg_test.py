import re
from enum import Enum

import mitmproxy.http

from Middleware.split import changeRequest, extractResponse
from utils import printInfo, printWarn


class Status(Enum):
    OK = 1
    Error = 0


class Router:
    def __init__(self):
        printInfo("init Router")

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # only intercept GET requests
        status, key = self.get_key_from_request(flow.request)
        if status == Status.OK:
            printInfo("status: OK")
            print(f"query {self.start} {self.end}")
            flow.request = changeRequest(
                flow.request,
                max(self.start - 100000, 0), self.end + 100000,
                ori_range=(self.start, self.end))

    def response(self, flow: mitmproxy.http.HTTPFlow):
        request = flow.request
        if request.method == "GET":
            status, key = self.get_key_from_request(request)
            if status == Status.OK:
                print(len(flow.response.content))
                start, end = map(
                    int, flow.request.headers["ori-range"].split(","))
                flow.response = extractResponse(flow.response, start, end)
                print(len(flow.response.content))
                # print(flow.response.headers)
            # with open("response", "wb") as f:
            #     pickle.dump(flow.response, f)
            # print(flow.response.headers)

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
        if status == Status.OK:
            start, end = range.split("-")
            self.start = int(start)
            self.end = int(end)
        return status, "-".join([referer, filename, range])


addons = [
    Router()
]
