import asyncio
import time

from Middleware.local_DB import LocalDB
from Middleware.P2P.client import download
from Middleware.P2P.server import Server

host_ip = "127.0.0.1"

db = LocalDB(backend=None, max_size=10)
db.insert("Vi", "Powder " * 10)
db.printDB()

server = Server(db, host_ip)
server.start()

time.sleep(2)

asyncio.run(
    download("Vi", host_ip))

db.update("Vi", "Caitlyn " * 10)
db.printDB()

asyncio.run(
    download("Vi", host_ip))
