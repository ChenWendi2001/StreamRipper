from collections import defaultdict

from utils import printInfo


class Scheduler:
    def __init__(self, backend) -> None:
        self.backend = backend
        self.download_num = defaultdict(int)
        self.alpha = 50

    def schedule(self):
        hosts = self.backend.query("STATUS")
        best_host, best_score = None, float("-inf")
        for host, speed in hosts:
            download_num = self.download_num[host]
            score = speed + self.alpha / (download_num + 1)
            if score > best_score:
                best_score = score
                best_host = host

        printInfo("best score {:>.4f}".format(score))
        self.download_num[best_host] += 1

        return best_host
