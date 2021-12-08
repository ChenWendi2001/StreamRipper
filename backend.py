import json
import os
import re
import subprocess
import time

import requests
from icecream import ic

from utils import getHostIP, printError, printInfo, printWarn


class BackendServer:
    def __init__(self, disco_id, host_ip,
                 http_port=4001, raft_port=4002,
                 file_dir="rqlite_db", log_dir="rqlite_log"):
        self.disco_id = disco_id
        self.host_ip = host_ip
        self.http_port = http_port
        self.raft_port = raft_port
        self.file_dir = file_dir
        self.log_dir = log_dir

    @staticmethod
    def getDiscoID():
        # $ curl -XPOST -L -w "\n" 'http://discovery.rqlite.com'
        try:
            f = os.popen(
                "curl -XPOST -L -w '\n' 'http://discovery.rqlite.com' 2>/dev/null")
            result = json.loads(f.read())
            return result["disco_id"]
        except Exception as e:
            print(e)
            printError(True, "fail to get id")

    def __enter__(self):
        # $ rqlited -disco-id <disco ID>

        if os.path.exists(self.file_dir):
            import shutil
            shutil.rmtree(self.file_dir)

        self.log_file = open(self.log_dir, "w")
        self.proc = subprocess.Popen(
            ["./rqlited",
             "-http-addr", f"{self.host_ip}:{self.http_port}",
             "-raft-addr", f"{self.host_ip}:{self.raft_port}",
             "-disco-id", self.disco_id, self.file_dir],
            stdout=self.log_file, stderr=self.log_file)

        try:
            self.proc.wait(timeout=4)
            printError(True, f"fail to join cluster {self.disco_id}")
        except subprocess.TimeoutExpired:
            printInfo(f"join cluster {self.disco_id}")

    def __exit__(self, *_):
        # $ curl -XDELETE -L --post301 http://discovery.rqlite.com/<disco ID>
        #   -H "Content-Type: application/json" -d '{"addr": "<node address>"}'
        try:
            f = os.popen(
                "curl -XDELETE -L --post301"
                f" http://discovery.rqlite.com/{self.disco_id}"
                " -H 'Content-Type: application/json'"
                f" -d '{{\"addr\": \"{self.host_ip}:{self.http_port}\"}}' 2>/dev/null")
            result = json.loads(f.read())
            printInfo(f"stop current node, rest nodes {result['nodes']}")
        except Exception as e:
            print(e)
            printWarn(True, "fail to stop")
            return False
        finally:
            printInfo("quit.")
            self.proc.terminate()
            self.log_file.close()


# sample
id = BackendServer.getDiscoID()
with BackendServer(ic(id), getHostIP()) as server:
    time.sleep(2)
