import random

from icecream import ic
from tqdm import tqdm

from Backend.backend import BackendServer
from Middleware.local_DB import LocalDB
from utils import getHostIP

disco_id = BackendServer.getDiscoID()
host_ip = getHostIP()

with BackendServer(ic(disco_id), ic(host_ip)) as server:
    max_size = int(1e4)
    db = LocalDB(server, max_size)

    for i in tqdm(range(max_size * 2)):
        key = random.randint(0, max_size * 10)
        if db.query(key) is None:
            db.insert(key, 0)

    db.printDB()
    server.printDB()
