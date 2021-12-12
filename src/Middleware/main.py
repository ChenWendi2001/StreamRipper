import asyncio
import json
import pickle

import requests
from Backend.backend import BackendServer
from mitmproxy import http
from utils import getHostIP, printError, printInfo, printWarn

from .local_DB import LocalDB
from .P2P.client import download
from .P2P.server import Server
from .scheduler.scheduler import Scheduler
from .scheduler.speed_test import SpeedTester
from .split import Splitter


def main_func(task_queue, done_queue):
    """[summary]
    key = {BV..}-{30..}-{RANGE} 
    e.g. "BV1fS4y1X7on-30032-214012-463769"
    ("query", key, request)
    ("insert", key, pickle.dumps(flow.response))
    """
    # node type
    with open("config.json", "r") as f:
        config = json.load(f)

    host_type = config["type"]
    disco_id = config["disco_id"]

    printInfo("\033[41m start main \033[0m")
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
        if host_type == "server":
            tester = SpeedTester(server)
            tester.start()
        # scheduler
        scheduler = Scheduler(server)

        splitter = Splitter(
            host_type, done_queue, scheduler, server, db)

        while True:
            item = task_queue.get()
            opt, key = item[:-1]

            if opt == "insert":
                # insert
                splitter.insert(key, item[-1])

            if opt == "query":
                # query
                splitter.query(key, item[-1])
                continue

                printInfo(f"query {key}")
                result = server.query("PACK", key)

                # downloader
                if result:
                    # NOTE: find host
                    target_ip = result[0][-1]
                    result = asyncio.run(
                        download(key, target_ip))
                    printInfo("\033[42m frontend hit \033[0m")
                    done_queue.put(result)
                    continue

                # database miss
                # if the best host is current host return None
                if host_type == "server":
                    done_queue.put("")
                    continue

                # schedule -> get a best host to download
                best_host_ip = scheduler.schedule()

                # send download request(host+http request)
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
