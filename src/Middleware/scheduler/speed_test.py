import threading
import time

import speedtest
from utils import printInfo


class SpeedTester(threading.Thread):
    def __init__(self, backend, period=600) -> None:
        super().__init__(daemon=True)
        self.backend = backend
        self.period = period
        self.speed_test = speedtest.Speedtest()

    def run(self):
        self.backend.modify(
                    "STATUS", (self.backend.host_ip, 10))
        while True:
            self.speed_test.get_best_server()
            self.speed_test.download(threads=0)
            results = self.speed_test.results.dict()
            download_speed = results["download"] / 1048576
            printInfo("download speed {:>.4f}".format(download_speed))

            if not self.backend is None:
                self.backend.modify(
                    "STATUS", (self.backend.host_ip, download_speed))

            time.sleep(self.period)
