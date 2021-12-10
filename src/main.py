from multiprocessing import Queue
from Backend.backend import BackendServer
from Middleware.local_DB import LocalDB
from Middleware.P2P.client import download
from Middleware.P2P.server import Server
from icecream import ic

import asyncio


def main(disco_id, task_queue, done_queue):
    # BUG: FIXME:
    disco_id = BackendServer.getDiscoID()
    host_ip = "172.0.0.1"

    with BackendServer(ic(disco_id), ic(host_ip)) as server:
        db = LocalDB(backend=server, max_size=10)
        db.printDB()
        server.printDB()

        p2p_server = Server(db, host_ip)
        p2p_server.start()

        while True:
            item = task_queue.get()

            if len(item) == 1:
                # query
                result = server.query("PACK", item[0])
                if result:
                    target_ip = result[0][-1]
                    result = asyncio.run(
                        download(item[0], ic(target_ip)))
                done_queue.put(result)
            else:
                # insert
                db.insert(*item)
