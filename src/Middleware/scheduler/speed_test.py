import threading
import time

import speedtest
from icecream import ic


class SpeedTester(threading.Thread):
    def __init__(self, backend, period=30) -> None:
        super().__init__(daemon=True)
        self.backend = backend
        self.period = period
        self.speed_test = speedtest.Speedtest()

    def run(self):
        while True:
            self.speed_test.get_best_server()
            self.speed_test.download(threads=0)
            results = self.speed_test.results.dict()
            download_speed = results["download"] / 1048576
            ic(download_speed)

            if not self.backend is None:
                self.backend.modify(
                    "STATUS", (self.backend.host_ip, download_speed))

            time.sleep(self.period)
