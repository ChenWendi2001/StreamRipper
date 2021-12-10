import mitmproxy.http
from mitmproxy import ctx

from enum import Enum
from queue import Queue
import threading


import asyncio
import sys

class Status(Enum):
    OK = 1
    Error = 2


def main(task_queue: Queue, down_queue: Queue):
    while True:
        value = task_queue.get()
        print('Get %s from queue.' % value, file=sys.stdout)


class Router:
    def __init__(self):
        print("123", file=sys.stdout)
        self.task_queue, self.done_queue = Queue(), Queue()
        self.t_main= threading.Thread(target=main, args=(self.task_queue,self.done_queue),daemon=True)
        self.t_main.start()

    def __del__(self):
        # self.p_midware.terminate()
        print("del", file=sys.stdout)

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # only intercept GET requests
        request = flow.request
        if request.method == "GET":
            status,key = self.get_key_from_request(request)
            if status == Status.OK:
                ctx.log.info("OK")
                ctx.log.info(key)
                self.task_queue.put((key,))
                data = self.done_queue.get()
                if data != None:
                    flow.response(data)
            else:
                ctx.log.info("Error")

    def response(self, flow: mitmproxy.http.HTTPFlow):
        #TODO
        request = flow.request
        if request.method == "GET":
            status,key = self.get_key_from_request(request)
            if status == Status.OK:
                response = flow.request
                self.task_queue.put((key, response))
        pass

    def http_connect(self, flow: mitmproxy.http.HTTPFlow):  
        # for future use
        pass

    def get_key_from_request(self, request):
        # get file name
        path = request.path
        filename = path[:path.find(".m4s")].split("/")[-1]

        # request header (contains referer and range)
        header = request.headers
        referer= header.get("referer", default="no referer")
        range = header.get("range", default="no range").lstrip("bytes=")
        
        #parse
        if referer != "no referer":
            referer = referer[referer.find("BV"):]
            split = [referer.find("?") if referer.find("?")!=-1 else 1000,
                    referer.find("/") if referer.find("/")!=-1 else 1000]
            referer = referer[:min(split)]

        if referer != "no referer" and range != "no range":
            status = Status.OK
        else:
            status = Status.Error
        
        return status,"-".join([referer, filename, range])

addons = [
    Router()
]