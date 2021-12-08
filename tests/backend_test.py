from re import I
from backend import BackendServer
from icecream import ic
from utils import getHostIP
import random


disco_id = BackendServer.getDiscoID()
ip = getHostIP()
with BackendServer(ic(disco_id), ic(ip)) as server:
    server.printDB()
    server.insert("PACK", (
        (hash("FIND"), random.random()), ))
    server.insert("STATUS", (
        (hash("DDL"), random.random()), ))
    server.printDB()

    print(server.query("PACK", hash("FIND")))
    print(server.query("PACK", hash("DDL")))

    server.remove("PACK", hash("FIND"))
    server.printDB()

    server.modify("STATUS", (hash("DDL"), 555))
    server.printDB()
