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
    printInfo(f"type: {host_type}")

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
                splitter.insert(key, item[-1])

            if opt == "query":
                splitter.query(key, item[-1])

            printError(
                opt != "insert" and opt != "query",
                "invalid key")
