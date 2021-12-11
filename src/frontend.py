import mitmproxy.http
from mitmproxy import ctx, http

from enum import Enum
from queue import Queue
import threading
# from multiprocessing import Process

from Backend.backend import BackendServer
from Middleware.local_DB import LocalDB
from Middleware.P2P.client import download
from Middleware.P2P.server import Server

from Middleware.scheduler.speed_test import SpeedTester
from Middleware.scheduler.scheduler import Scheduler

import asyncio
import sys
import re
import pickle
import requests
import json

from icecream import ic
from utils import printInfo, printWarn, getHostIP


class Status(Enum):
    OK = 1
    Error = 2

# def scheduler():
#     return "127.0.0.1"

def main(disco_id, task_queue, done_queue):
    # BUG: FIXME:

    # node type
    with open("./config/config.json","r") as f:
        config = json.load(f)

    type = config["type"]
    disco_id = config["disco_id"]

    printInfo("\033[31m start main \033[0m")
    if disco_id == "": disco_id = BackendServer.getDiscoID()
    host_ip = getHostIP()

    with BackendServer(disco_id, host_ip) as server:
        db = LocalDB(backend=server, max_size=10000)
        # db.printDB()
        # server.printDB()

        p2p_server = Server(db, host_ip)
        p2p_server.start()

        # speedtest
        if type == "server":
            tester = SpeedTester(server)
            tester.start()
        # scheduler
        scheduler = Scheduler(server)

        while True:
            item = task_queue.get()

            if item[2] == "query":
                # query
                printInfo(f"query {item[0]}")
                result = server.query("PACK", item[0])
                # downloader
                if result:
                    target_ip = result[0][-1]
                    result = asyncio.run(
                        download(item[0], target_ip))
                    printInfo("\033[42m frontend hit \033[0m")
                else:
                    # schedule -> get a best host to download
                    if type != "server":
                        best_host_ip = scheduler.schedule()
                    else:
                        best_host_ip = host_ip

                    # if the best host is current host return None
                    if best_host_ip == host_ip:
                        result = ""
                    # else send download request(host+http request)
                    # remember to set a mark in request headers to represent download request
                    else:
                        printInfo(f"use other host:{best_host_ip} to download")
                        request = item[1]
                        url, headers = request.pretty_url, request.headers.fields
                        headers = {k.decode():v.decode() for k,v in headers}
                        headers["scheduler"] = "True"
                        response = requests.get(url, headers=headers, proxies={"https":best_host_ip+":8080"},verify=False)
                    # download data
                        result = http.Response.make(status_code = response.status_code, 
                                                    content = response.content, 
                                                    headers = dict(response.headers))
                        result = pickle.dumps(result)

                done_queue.put(result)
            elif item[2] == "insert":
                # insert
                if db.query(item[0]) is None:
                    printInfo(f"insert {item[0]}")
                    db.insert(*item[:-1])


class Router:
    from_database = False

    def __init__(self):
        printInfo("init Rounter")
        self.task_queue, self.done_queue = Queue(), Queue()
        self.t_main = threading.Thread(target=main,
                                       args=(None, self.task_queue, self.done_queue), daemon=True)
        self.t_main.start()

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # only intercept GET requests
        self.from_database = False
        request = flow.request
        # filter
        headers = request.headers
        scheduler_flag = headers.get("scheduler", default="False")
        if scheduler_flag == "True":
            printInfo("\033[44m receive a delegation \033[0m")
            return
        if request.method == "GET":
            status, key = self.get_key_from_request(request)
            if status == Status.OK:
                printInfo("status: OK")
                self.task_queue.put((key,request, "query"))
                data = self.done_queue.get()
                printInfo(f"get data {data[:10]}")
                if data:
                    response = pickle.loads(data)
                    response.headers["Server"] = "StreamRipper"
                    flow.response = response
                    self.from_database = True
            else:
                printWarn(True, "status: Error")

    def response(self, flow: mitmproxy.http.HTTPFlow):
        # TODO
        request = flow.request
        if request.method == "GET":
            status, key = self.get_key_from_request(request)
            if status == Status.OK:
                response = flow.response
                if not self.from_database:
                    self.task_queue.put((key, pickle.dumps(response), "insert"))
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
        headers = request.headers
        referer = headers.get("referer", default="no referer")
        range = headers.get("range", default="no range").lstrip("bytes=")

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
