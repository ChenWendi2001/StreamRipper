import socket
import sys


def printInfo(msg):
    print("[INFO]: {}".format(msg), file=sys.stdout)


def printWarn(flag, msg):
    if not flag:
        return
    print("[WARN]: {}".format(msg), file=sys.stderr)


def printError(flag, msg):
    if not flag:
        return
    print("[ERROR]: {}".format(msg), file=sys.stderr)
    sys.exit(0)


def getHostIP():
    s = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
