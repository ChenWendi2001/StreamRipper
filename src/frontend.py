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

class Status(Enum):
    OK = 1
    Error = 2

def main(disco_id, task_queue, done_queue):
    # BUG: FIXME:
    ic("*******entering main*******")
    disco_id = BackendServer.getDiscoID()
    host_ip = "127.0.0.1"

    with BackendServer(disco_id, host_ip) as server:
        db = LocalDB(backend=server, max_size=1000)
        db.printDB()
        server.printDB()

        p2p_server = Server(db, host_ip)
        p2p_server.start()

        while True:
            item = task_queue.get()
            ic(item[0])

            if len(item) == 1:
                # query
                result = server.query("PACK", item[0])
                if result:
                    target_ip = result[0][-1]
                    result = asyncio.run(
                        download(item[0], target_ip))
                done_queue.put(result)
            else:
                # insert
                db.insert(*item)



class Router:
    def __init__(self):
        ic("******* init Rounter *******")
        self.task_queue, self.done_queue = Queue(), Queue()
        self.t_main= threading.Thread(target=main, 
            args=(None, self.task_queue,self.done_queue),daemon=True)
        self.t_main.start()

    def __del__(self):
        # self.p_midware.terminate()
        ic("******* exit Rounter *******")

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # only intercept GET requests
        request = flow.request
        if request.method == "GET":
            status,key = self.get_key_from_request(request)
            ic(key)
            if status == Status.OK:
                ic("OK")
                self.task_queue.put((key,))
                data = self.done_queue.get()
                ic(data)
                if data:
                    ic("*************** hit **************")
                    flow.response(pickle.loads(data))
            else:
                ic("Error")
    def response(self, flow: mitmproxy.http.HTTPFlow):
        #TODO
        request = flow.request
        if request.method == "GET":
            status,key = self.get_key_from_request(request)
            if status == Status.OK:
                response = flow.response
                self.task_queue.put((key, pickle.dumpys(response)))
        pass

    def http_connect(self, flow: mitmproxy.http.HTTPFlow):  
        # for future use
        pass

    def get_key_from_request(self, request):
        # get file name
        path = request.path
        ic(path)
        if path.find(".m4s") == -1: return Status.Error, None
        filename = path[:path.find(".m4s")].split("/")[-1]

        # request header (contains referer and range)
        header = request.headers
        referer= header.get("referer", default="no referer")
        range = header.get("range", default="no range").lstrip("bytes=")
        
        #parse
        if referer != "no referer":
            referer = referer[referer.find("BV"):]
            referer = re.search("(BV\w+)",referer).group()

        if referer != "no referer" and range != "no range":
            status = Status.OK
        else:
            status = Status.Error
        
        return status,"-".join([referer, filename, range])

addons = [
    Router()
]