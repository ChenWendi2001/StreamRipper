import asyncio
import threading

from utils import printInfo


class Server(threading.Thread):
    def __init__(self, local_db, host_ip, port=4003) -> None:
        super().__init__(daemon=True)
        self.local_db = local_db
        self.host_ip = host_ip
        self.port = port

    async def query(self, reader, writer):
        data = await reader.read(100)
        key = data.decode()

        addr = writer.get_extra_info("peername")
        print(f"Received {key} from {addr}")

        data = self.local_db.query(key)
        if not data is None:
            printInfo("server hit")
        writer.write(data)
        await writer.drain()

        print("Close the connection")
        writer.close()

    async def listen(self):
        server = await asyncio.start_server(
            self.query, self.host_ip, self.port)

        print(f"Serving on {self.host_ip}:{self.port}")

        async with server:
            await server.serve_forever()

    def run(self):
        asyncio.run(self.listen())
