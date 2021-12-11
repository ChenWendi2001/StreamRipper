from Backend.backend import BackendServer
from utils import getHostIP
from Middleware.scheduler.scheduler import Scheduler
from Middleware.scheduler.speed_test import SpeedTester
import time


disco_id = BackendServer.getDiscoID()
host_ip = getHostIP()
with BackendServer(disco_id, host_ip) as server:
    tester = SpeedTester(server)
    tester.start()

    time.sleep(20)
    scheduler = Scheduler(server)
    while True:
        print(scheduler.schedule())
        # time.sleep(2)
