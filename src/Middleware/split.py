import pickle
from utils import printInfo
import copy
import asyncio

from Middleware.P2P.client import download


class Splitter:
    def __init__(self, done_queue, backend, local_db) -> None:
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

    def split(self, v_range):
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

    def query(self, v_range, offset, file_name):
        slices = self.split(v_range)
        result = None
        for start, end in slices:
            start, end = self.getblock(start, end)
            # query
            key = file_name.format(
                "-".join([start + offset, end + offset]))
            printInfo(f"query {key}")
            block = self.backend.query("PACK", key)
            if result:
                target_ip = result[0][-1]
                result = asyncio.run(
                    download(key, target_ip))
        done_queue.put(result)

    def merge():
        pass

    def insert(self, v_range, offset, file_name, response):
        slices = self.split(v_range)
        # insert complete blocks
        for start, end in slices:
            if end - start + 1 == self.block_size:
                # insert
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
s = Splitter(None)
s.block_size = 256
print(s.split((1, 255)))
print(s.split((0, 255)))
print(s.split((256, 511)))
print(s.split((255, 512)))
print(s.split((128, 550)))
