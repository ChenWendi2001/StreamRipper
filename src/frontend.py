import mitmproxy.http
from mitmproxy import ctx

from enum import Enum
from queue import Queue
import threading

from Backend.backend import BackendServer
from Middleware.local_DB import LocalDB
from Middleware.P2P.client import download
from Middleware.P2P.server import Server

import asyncio
import sys
import re
import pickle

from icecream import ic
from utils import printInfo, printWarn


class Status(Enum):
    OK = 1
    Error = 2


def main(disco_id, task_queue, done_queue):
    # BUG: FIXME:
    printInfo("\033[31m start main \033[0m")
    disco_id = BackendServer.getDiscoID()
    host_ip = "127.0.0.1"

    with BackendServer(disco_id, host_ip) as server:
        db = LocalDB(backend=server, max_size=10000)
        # db.printDB()
        # server.printDB()

        p2p_server = Server(db, host_ip)
        p2p_server.start()

        while True:
            item = task_queue.get()

            if len(item) == 1:
                # query
                printInfo(f"query {item[0]}")
                result = server.query("PACK", item[0])
                if result:
                    target_ip = result[0][-1]
                    result = asyncio.run(
                        download(item[0], target_ip))
                done_queue.put(result)
            else:
                # insert
                if db.query(item[0]) is None:
                    printInfo(f"insert {item[0]}")
                    db.insert(*item)


class Router:
    def __init__(self):
        printInfo("init Rounter")
        self.task_queue, self.done_queue = Queue(), Queue()
        self.t_main = threading.Thread(target=main,
                                       args=(None, self.task_queue, self.done_queue), daemon=True)
        self.t_main.start()

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # only intercept GET requests
        request = flow.request
        if request.method == "GET":
            status, key = self.get_key_from_request(request)
            if status == Status.OK:
                printInfo("status: OK")
                self.task_queue.put((key,))
                data = self.done_queue.get()
                printInfo(f"get data {data[:10]}")
                if data:
                    printInfo("\033[42m frontend hit \033[0m")
                    response = pickle.loads(data)
                    response.headers["Server"] = "StreamRipper"
                    flow.response = response
            else:
                printWarn(True, "status: Error")

    def response(self, flow: mitmproxy.http.HTTPFlow):
        # TODO
        request = flow.request
        if request.method == "GET":
            status, key = self.get_key_from_request(request)
            if status == Status.OK:
                response = flow.response
                self.task_queue.put((key, pickle.dumps(response)))
        pass

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
        header = request.headers
        referer = header.get("referer", default="no referer")
        range = header.get("range", default="no range").lstrip("bytes=")

        # parse
        if referer != "no referer":
            referer = referer[referer.find("BV"):]
            referer = re.search("(BV\w+)", referer).group()

        if referer != "no referer" and range != "no range":
            status = Status.OK
        else:
            status = Status.Error

        return status, "-".join([referer, filename, range])


addons = [
    Router()
]
