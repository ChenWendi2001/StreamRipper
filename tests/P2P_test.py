import asyncio
import time

from icecream import ic

from Backend.backend import BackendServer
from Middleware.local_DB import LocalDB
from Middleware.P2P.client import download
from Middleware.P2P.server import Server


disco_id = BackendServer.getDiscoID()
host_ip = "127.0.0.1"

with BackendServer(ic(disco_id), ic(host_ip)) as server:
    db = LocalDB(backend=server, max_size=10)
    db.insert("Vi", ("Powder " * 10).encode())
    db.printDB()
    server.printDB()

    p2p_server = Server(db, host_ip)
    p2p_server.start()

    time.sleep(2)

    result = server.query("PACK", "Vi")
    if result:
        target_ip = result[0][-1]
        asyncio.run(
            download("Vi", ic(target_ip)))

    db.update("Vi", ("Caitlyn " * 10).encode())
    db.printDB()

    result = server.query("PACK", "Vi")
    if result:
        target_ip = result[0][-1]
        asyncio.run(
            download("Vi", ic(target_ip)))
