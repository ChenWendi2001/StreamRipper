from collections import OrderedDict
from threading import Lock


class LocalDB:
    def __init__(self, backend, max_size) -> None:
        # NOTE: local mode: backend is None
        self.backend = backend
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
        if not self.backend is None:
            self.backend.insert(
                "PACK", ((key, self.backend.host_ip), ))

        # evict
        if len(self.lru_cache) > self.max_size:
            # NOTE: remove item from local and global DB
            k, _ = self.lru_cache.popitem(last=False)
            if not self.backend is None:
                self.backend.remove("PACK", k)

        self.lock.release()

    def update(self, key, value):
        self.lock.acquire()

        if not key in self.lru_cache:
            raise KeyError()
        self.lru_cache.move_to_end(key)
        self.lru_cache[key] = value

        self.lock.release()

    def query(self, key):
        if key in self.lru_cache:
            self.lru_cache.move_to_end(key)
            return self.lru_cache[key]

        # HACK: FIXME:
        # A --> B
        # A query backend ---> B delete ---> A query B
        return None
