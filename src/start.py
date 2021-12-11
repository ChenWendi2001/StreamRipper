import json
import subprocess

from utils import printError, printInfo


def main():
    type = int(input(
        "Please input your node type:",
        "([1] server [2] client):"))
    printError(
        type != 1 and type != 2,
        "Invalid node type.")

    type = ["", "server", "client"][type]

    disco_id = input("Please input disco ID (empty for the first node):")
    printError(
        type == "client" and disco_id == "",
        "A client should have a discover ID.")

    with open("./config/config.json", "w") as f:
        json.dump({"type": type, "disco_id": disco_id}, f)

    mitm_proc = None
    try:
        mitm_proc = subprocess.Popen(
            ["mitmweb", "-s", "frontend.py"])
        mitm_proc.wait()

    except KeyboardInterrupt:
        printInfo("catch keyboard interrupt")
        printInfo(mitm_proc.pid)

    finally:
        mitm_proc.kill()
        mitm_proc.wait()


if __name__ == "__main__":
    main()
