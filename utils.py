import socket


def printInfo(msg):
    print("[INFO]: {}".format(msg))


def printWarn(flag, msg):
    if not flag:
        return
    print("[WARN]: {}".format(msg))


def printError(flag, msg):
    if not flag:
        return
    print("[ERROR]: {}".format(msg))
    import sys
    sys.exit(0)


def getHostIP():
    s = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


if __name__ == "__main__":
    print(getHostIP())
