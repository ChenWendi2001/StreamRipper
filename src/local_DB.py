from collections import OrderedDict
from icecream import ic
from threading import Lock


class LocalDB:
    def __init__(self, max_size) -> None:
        self.max_size = max_size
        self.lru_cache = OrderedDict()
        self.lock = Lock()

    def printDB(self):
        """[summary]
        debug function
        """
        print(self.lru_cache)

    def insert(self, key, value):
        self.lock.acquire()
        self.lru_cache[key] = value
        if ic(len(self.lru_cache)) > self.max_size:
            self.lru_cache.popitem(last=False)
        self.lock.release()

    def query(self, key):
        if key in self.lru_cache:
            self.lru_cache.move_to_end(key)
            return self.lru_cache[key]
        return None
