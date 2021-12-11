import json
import subprocess
import os
import signal
from utils import printError, printInfo

def main():
    type = int(input("Please input your node type:([1] server [2] client):"))
    printError(type!=1 and type !=2, "Invalid node type.")
    type = ["","server", "client"][type]

    disco_id = input("Please input disco ID (empty for the first node):")
    if type == "client":
        printError(disco_id=="", "A client shoude have a discover ID.")
    
    with open("./config/config.json","w") as f:
        json.dump({"type": type, "disco_id":disco_id}, f)
    
    mitm = None
    try:
        mitm = subprocess.Popen(["mitmweb","-s","frontend.py"])
        mitm.wait()
    except KeyboardInterrupt:
        printInfo("catch keyboard interrupt")   
    finally:
        # os.killpg(os.getpgid(mitm.pid), signal.SIGTERM)
        mitm.terminate()
        mitm.wait()
        pass


if __name__ == "__main__":
    main()