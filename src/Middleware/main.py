import asyncio
import json
import pickle

import requests
from Backend.backend import BackendServer
from mitmproxy import http
from utils import getHostIP, printError, printInfo, printWarn

from Middleware.local_DB import LocalDB
from Middleware.P2P.client import download
from Middleware.P2P.server import Server
from Middleware.scheduler.scheduler import Scheduler
from Middleware.scheduler.speed_test import SpeedTester


def main_func(task_queue, done_queue):
    """[summary]
    ("query", key, request)
    ("insert", key, pickle.dumps(flow.response))
    """
    # BUG: FIXME:

    # node type
    with open("./config/config.json", "r") as f:
        config = json.load(f)

    type = config["type"]
    disco_id = config["disco_id"]

    printInfo("\033[31m start main \033[0m")
    if disco_id == "":
        disco_id = BackendServer.getDiscoID()
    host_ip = getHostIP()

    with BackendServer(disco_id, host_ip) as server:
        db = LocalDB(backend=server, max_size=10000)
        # db.printDB()
        # server.printDB()

        p2p_server = Server(db, host_ip)
        p2p_server.start()

        # speed test
        if type == "server":
            tester = SpeedTester(server)
            tester.start()
        # scheduler
        scheduler = Scheduler(server)

        while True:
            item = task_queue.get()
            opt, key = item[:-1]

            if opt == "insert":
                # insert
                if db.query(key) is None:
                    printInfo(f"insert {key}")
                    db.insert(key, item[-1])

            if opt == "query":
                # query
                printInfo(f"query {key}")
                result = server.query("PACK", item[-1])

                # downloader
                if result:
                    # NOTE: find host
                    target_ip = result[0][-1]
                    result = asyncio.run(
                        download(item[0], target_ip))
                    printInfo("\033[42m frontend hit \033[0m")
                else:
                    # schedule -> get a best host to download
                    best_host_ip = host_ip
                    if type != "server":
                        best_host_ip = scheduler.schedule()

                    # if the best host is current host return None
                    if best_host_ip == host_ip:
                        done_queue.put(result)
                        continue

                    # else send download request(host+http request)
                    # remember to set a mark in request headers to represent download request
                    printInfo(f"use other host:{best_host_ip} to download")

                    request = item[-1]
                    url, headers = request.pretty_url, request.headers.fields
                    headers = {k.decode(): v.decode() for k, v in headers}
                    headers["scheduler"] = "True"

                    try:
                        response = requests.get(
                            url, headers=headers,
                            proxies={"https": best_host_ip+":8080"},
                            verify=False, timeout=4)

                        # download data
                        result = http.Response.make(
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            content=response.content,)
                        result = pickle.dumps(result)

                    except:
                        request = ""

                done_queue.put(result)

            printError(
                opt != "insert" and opt != "query",
                "invalid key")
