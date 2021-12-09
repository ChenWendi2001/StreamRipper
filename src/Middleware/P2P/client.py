import asyncio


async def download(key, host_ip, port=4003):
    reader, writer = await asyncio.open_connection(
        host_ip, port)

    print(f"Download: {key}")
    writer.write(key.encode())

    data = await reader.read(-1)
    print(f"Received: {data.decode()}")

    print("Close the connection")
    writer.close()

    return data.decode()
