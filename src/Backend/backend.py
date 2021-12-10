import json
import os
import subprocess

import pyrqlite.dbapi2 as dbapi2
from utils import printError, printInfo, printWarn


class BackendServer:
    def __init__(self, disco_id, host_ip,
                 http_port=4001, raft_port=4002,
                 file_dir="rqlite_db", log_dir="rqlite_log"):
        self.disco_id = disco_id
        self.host_ip = host_ip
        self.http_port = http_port
        self.raft_port = raft_port
        self.file_dir = file_dir
        self.log_dir = log_dir
        self.connection = None

    @staticmethod
    def getDiscoID():
        # $ curl -XPOST -L -w "\n" 'http://discovery.rqlite.com'

        try:
            f = os.popen(
                "curl -XPOST -L -w '\n' 'http://discovery.rqlite.com' 2>/dev/null")
            result = json.loads(f.read())
            return result["disco_id"]
        except Exception as e:
            print(e)
            printError(True, "fail to get id")

    def __enter__(self):
        """[summary]
        automatically form cluster
        """
        # $ rqlited -disco-id <disco ID>

        if os.path.exists(self.file_dir):
            import shutil
            shutil.rmtree(self.file_dir)

        self.log_file = open(self.log_dir, "w")
        self.proc = subprocess.Popen(
            ["./rqlited",
             "-http-addr", f"{self.host_ip}:{self.http_port}",
             "-raft-addr", f"{self.host_ip}:{self.raft_port}",
             "-disco-id", self.disco_id, self.file_dir],
            stdout=self.log_file, stderr=self.log_file)

        try:
            self.proc.wait(timeout=10)
            printError(True, f"fail to join cluster {self.disco_id}")
        except subprocess.TimeoutExpired:
            printInfo(f"join cluster {self.disco_id}")
            self.connection = dbapi2.connect(
                host=self.host_ip, port=self.http_port)
            self.createTables()
            return self

    def __exit__(self, *_):
        """[summary]
        remove self from cluster
        """
        # $ curl -XDELETE -L --post301 http://discovery.rqlite.com/<disco ID>
        #   -H "Content-Type: application/json" -d '{"addr": "<node address>"}'

        try:
            f = os.popen(
                "curl -XDELETE -L --post301"
                f" http://discovery.rqlite.com/{self.disco_id}"
                " -H 'Content-Type: application/json'"
                f" -d '{{\"addr\": \"{self.host_ip}:{self.http_port}\"}}' 2>/dev/null")
            result = json.loads(f.read())
            printInfo(f"stop current node, rest nodes {result['nodes']}")
        except Exception as e:
            print(e)
            printWarn(True, "fail to stop")
            return False
        finally:
            printInfo("quit.")
            self.connection.close()
            self.proc.terminate()
            self.log_file.close()

    def printDB(self,
                tables=["PACK", "STATUS"]):
        """[summary]
        debug function
        """
        with self.connection.cursor() as cursor:
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                print(f"{table}: ", cursor.fetchall())

    def createTables(self):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS PACK "
                "(ID TEXT NOT NULL PRIMARY KEY, IP TEXT)")
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS STATUS "
                "(ID TEXT NOT NULL PRIMARY KEY, SPEED REAL)")

    def query(self, table, column=None):
        """[summary]
        Args:
            table ([type]): [description]
            column (int): [description]. Defaults to None.
        Returns:
            result (tuple): [description]. 
                e.g. OrderedDict([('ID', x), ('IP', y)])
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM {} {}".format(
                    table, "" if column is None else f"WHERE ID = '{column}'")
            )
            result = cursor.fetchall()
        return result

    def insert(self, table, items):
        """[summary]
        Args:
            table ([type]): [description]
            items (tuple): [description]. e.g. ((1, 10), (2, 20))
        """
        with self.connection.cursor() as cursor:
            cursor.executemany(
                f"INSERT INTO {table} VALUES (?, ?)",
                seq_of_parameters=items)

    def remove(self, table, column):
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM {table} WHERE ID = '{column}'")

    def modify(self, table, item):
        """[summary]
        Args:
            table ([type]): [description]
            item (tuple): [description]. e.g. (1, 10)
        """
        self.remove(table, item[0])
        self.insert(table, (item, ))
