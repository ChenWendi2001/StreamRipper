import pickle

from utils import printError, printInfo

from .utils import (catResponse, changeRequest,
                    extractResponse, peerDelegate,
                    peerDownload)


def splitKey(key):
    # key = {BV..}-{30..}-{RANGE}
    # e.g. "BV1fS4y1X7on-30032-214012-463769"
    name, hash_id, low, high = key.split("-")
    v_range = (int(low), int(high))
    file_name = "-".join([name, hash_id, "{}"])
    return v_range, file_name


class Splitter:
    def __init__(self,
                 host_type, done_queue,
                 scheduler, backend, local_db) -> None:
        self.host_type = host_type
        self.done_queue = done_queue
        self.scheduler = scheduler
        self.backend = backend
        self.local_db = local_db
        self.block_size = 512 * 1024

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

    # NOTE: main API
    def insert(self, key, response):
        v_range, file_name = splitKey(key)
        printInfo(f"insert Key: {file_name}, {v_range}")

        slices = self.splitRange(v_range)
        for start, end in slices:
            key = file_name.format(f"{start}-{end}")
            result = self.backend.query("PACK", key)
            # avoid duplicate item
            if not result:
                printInfo(f"insert {key}")
                response_block = extractResponse(response, start, end)
                self.local_db.insert(key, pickle.dumps(response_block))

    # NOTE: main API
    def query(self, key, request):
        ori_range, file_name = splitKey(key)
        printInfo(f"query Key: {file_name}, {ori_range}")
        v_range = self.getBlock(*ori_range)

        host_ip = []
        slices = self.splitRange(v_range)
        for start, end in slices:
            key = file_name.format(f"{start}-{end}")
            printInfo(f"query {key}")
            response = self.backend.query("PACK", key)
            host_ip.append(
                None if not response else response[0][-1])

        # NOTE: server partial hit
        if self.host_type == "server" \
                and not all(host_ip):
            # content missing
            self.done_queue.put(
                (v_range, (ori_range)))
            return

        # NOTE: server all hit / client partial hit
        response = None
        for i, target_ip in enumerate(host_ip):
            start, end = slices[i]
            if target_ip is None:
                # peer delegate
                best_host_ip = self.scheduler.schedule()
                printInfo(f"use other host:{best_host_ip} to download")
                result = peerDelegate(
                    changeRequest(request, start, end, [start, end]),
                    best_host_ip)
                # timeout
                if not result:
                    # self download
                    self.done_queue.put(
                        (v_range, (ori_range)))
                    return
            else:
                # peer download
                key = file_name.format(f"{start}-{end}")
                result = peerDownload(key, target_ip)

            # concate content
            if response is None:
                response = pickle.loads(result)
                continue
            catResponse(response, pickle.loads(result))

        # extract response
        self.done_queue.put(pickle.dumps(
            extractResponse(response, *ori_range)))
