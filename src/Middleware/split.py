import asyncio
import copy
import pickle
import requests
import hashlib
import re

from utils import printError, printInfo

from Middleware.P2P.client import download


def splitKey(key):
    # key = {BV..}-{30..}-{RANGE}
    # e.g. "BV1fS4y1X7on-30032-214012-463769"
    name, hash_id, offset, high = key.split("-")
    v_range = int(high) - int(offset) + 1
    file_name = "-".join([name, hash_id, "{}"])
    return int(offset), v_range, file_name


def peerDownload(key, target_ip):
    result = asyncio.run(
        download(key, target_ip))
    printInfo(f"\033[42m frontend hit {key} \033[0m")
    return result


def changeRequest(request, start, end):
    # NOTE: [start, end] are ABSOLUTE index
    # for request, MODIFY THE FOLLOWING
    #   request.headers.range ("bytes={}-{}")
    new_request = copy.deepcopy(request)
    new_request.headers["range"] = f"bytes={start}-{end}"
    new_request.headers["debug"] = "Reorganization"
    return new_request


def extractResponse(response, start, end):
    # NOTE: [start, end] are RELATIVE index
    # for response, MODIFY THE FOLLOWING
    #   content-length, content-range
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
    # NOTE: concate new response to this
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


def peerDelegate(key, target_ip):
    pass


class Splitter:
    def __init__(self,
                 host_type, done_queue,
                 backend, local_db) -> None:
        self.host_type = host_type
        self.done_queue = done_queue
        self.backend = backend
        self.local_db = local_db
        self.block_size = 256 * 1024

    def __upper(self, k):
        # NOTE: k' % self.block_size == 0 & k' >= k
        return ((k - 1) // self.block_size + 1) * self.block_size

    def __lower(self, k):
        # NOTE: k' % self.block_size == 0 & k' <= k
        return k // self.block_size * self.block_size

    def splitRange(self, v_range):
        start, end = v_range
        # NOTE: lb >= start & rb <= end
        lb, rb = self.__upper(start), self.__lower(end)
        # NOTE: [start, lb - 1], [lb, rb), [rb, end]
        if rb < lb:
            return [v_range]

        slices = []
        if lb > start:
            slices.append((start, lb - 1))
        slices += [
            (i, i + self.block_size - 1)
            for i in range(lb, rb, self.block_size)]
        if end >= rb:
            slices.append((rb, end))

        return slices

    def getblock(self, start, end):
        # NOTE: start, end must be in the same block
        return (self.__lower(start), self.__upper(end) - 1)

    def query(self, key, request):
        offset, v_range, file_name = self.splitKey(key)

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
            return

        # NOTE: server all hit / client partial hit
        for i, target_ip in enumerate(host_ip):
            if not target_ip is None:
                start, end = slices[i]
                key = file_name.format(
                    "-".join([start + offset, end + offset]))
                # TODO: concate content
                result = self.peerDownload(key, target_ip)
            else:
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

    def insert(self, key, response):
        offset, v_range, file_name = self.splitKey(key)

        slices = self.splitRange(v_range)
        # insert complete blocks
        for start, end in slices:
            if end - start + 1 == self.block_size:
                key = file_name.format(
                    "-".join([start + offset, end + offset]))
                printInfo(f"insert {key}")
                response_block = copy.deepcopy(response)
                response_block.content = response_block.content[start: end + 1]
                self.local_db.insert(key, pickle.dumps(response_block))

        # NOTE: merge incomplete block if possible
        start, end = slices[0]
        if end - start + 1 < self.block_size:
            pass

        start, end = slices[-1]
        if end - start + 1 < self.block_size:
            pass


# test
# print(Splitter.splitKey(
#     "BV1fS4y1X7on-30032-214012-463769"))
# s = Splitter(None)
# s.block_size = 256
# print(s.split((1, 255)))
# print(s.split((0, 255)))
# print(s.split((256, 511)))
# print(s.split((255, 512)))
# print(s.split((128, 550)))
