import asyncio
import copy
import hashlib
import pickle
import re
from mitmproxy import http

import requests
from utils import printError, printInfo

from Middleware.P2P.client import download


def splitKey(key):
    # key = {BV..}-{30..}-{RANGE}
    # e.g. "BV1fS4y1X7on-30032-214012-463769"
    name, hash_id, offset, high = key.split("-")
    v_range = int(high) - int(offset) + 1
    file_name = "-".join([name, hash_id, "{}"])
    return int(offset), v_range, file_name


def changeRequest(request, start, end):
    """[summary]
    NOTE: [start, end] are ABSOLUTE index
    for request, MODIFY THE FOLLOWING
        request.headers.range ("bytes={}-{}")
    """
    new_request = copy.deepcopy(request)
    new_request.headers["range"] = f"bytes={start}-{end}"
    new_request.headers["debug"] = "Reorganization"
    return new_request


def extractResponse(response, start, end):
    """[summary]
    NOTE: [start, end] are RELATIVE index
    for response, MODIFY THE FOLLOWING
      content-length, content-range
    """
    new_response = copy.deepcopy(response)
    new_response.content = response.content[start:end + 1]
    new_response.headers["content-length"] = str(end - start + 1)
    low, length = re.search(
        "(\d+)-.+/(\d+)", response.headers["content-range"]).groups()
    new_response.headers["content-range"] = \
        f"{start + int(low)}-{end + int(low)}/{length}"
    new_response.headers["debug"] = "Reorganization"
    return new_response


def catResponse(this, response):
    """[summary]
    NOTE: concate new response to this
    """
    this.content += response.content
    l0, h0, len0 = map(int, re.search(
        "(\d+)-(\d+)+/(\d+)", this.headers["content-range"]).groups())
    l1, h1, len1 = map(int, re.search(
        "(\d+)-(\d+)+/(\d+)", response.headers["content-range"]).groups())
    printError(
        len0 != len1 or h0 + 1 != l1,
        "concate different responses")
    this.headers["content-length"] = str(h1 - l0 + 1)
    this.headers["content-range"] = f"{l0}-{h1}/{len0}"
    this.headers["debug"] = "Reorganization"


def peerDownload(key, target_ip):
    result = asyncio.run(
        download(key, target_ip))
    printInfo(f"\033[42m frontend hit {key} \033[0m")
    return result


def peerDelegate(request, target_ip):
    url = request.pretty_url
    headers = request.headers.fields
    headers = {k.decode(): v.decode() for k, v in headers}
    headers["scheduler"] = "True"

    try:
        response = requests.get(
            url, headers=headers,
            proxies={"https": target_ip + ":8080"},
            verify=False, timeout=4)

        # download data
        result = http.Response.make(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,)
        result = pickle.dumps(result)

    except:
        result = ""

    return result


class Splitter:
    def __init__(self,
                 host_type, done_queue,
                 scheduler, backend, local_db) -> None:
        self.host_type = host_type
        self.done_queue = done_queue
        self.scheduler = scheduler
        self.backend = backend
        self.local_db = local_db
        self.block_size = 256 * 1024

    def __upper(self, k):
        # NOTE: k' % self.block_size == 0 & k' >= k
        return (k // self.block_size + 1) * self.block_size

    def __lower(self, k):
        # NOTE: k' % self.block_size == 0 & k' <= k
        return k // self.block_size * self.block_size

    def getBlock(self, start, end):
        return (self.__lower(start), self.__upper(end) - 1)

    def splitRange(self, v_range):
        start, end = v_range
        # NOTE: lb >= start & rb <= end
        printError(
            start % self.block_size != 0 or
            (end + 1) % self.block_size != 0,
            "split irregular block")
        slices = [
            (i, i + self.block_size - 1)
            for i in range(start, end, self.block_size)]
        return slices

    def insert(self, key, response):
        # TODO: debug
        offset, v_range, file_name = self.splitKey(key)

        slices = self.splitRange(v_range)
        for start, end in slices:
            key = file_name.format(
                "-".join([start + offset, end + offset]))
            printInfo(f"insert {key}")
            response_block = extractResponse(response, start, end)
            self.local_db.insert(key, pickle.dumps(response_block))

    def query(self, key, request):
        offset, ori_range, file_name = self.splitKey(key)
        v_range = self.getBlock(*ori_range)

        host_ip = []
        slices = self.splitRange(v_range)
        for start, end in slices:
            key = file_name.format(
                "-".join([start + offset, end + offset]))
            printInfo(f"query {key}")
            result = self.backend.query("PACK", key)
            host_ip.append(
                None if not result else result[0][-1])

        # NOTE: server partial hit
        if self.host_type == "server" \
                and not all(host_ip):
            # content missing
            self.done_queue.put("")
            # TODO: extract downloads
            return

        # NOTE: server all hit / client partial hit
        for i, target_ip in enumerate(host_ip):
            if not target_ip is None:
                # peer download
                start, end = slices[i]
                key = file_name.format(
                    "-".join([start + offset, end + offset]))
                # TODO: concate content
                result = self.peerDownload(key, target_ip)
            else:
                # peer schedule
                best_host_ip = self.scheduler.schedule()
                printInfo(f"use other host:{best_host_ip} to download")

                # TODO: modify request
                result = peerDelegate(request, host_ip)
                if not result:
                    # TODO:
                    download self
