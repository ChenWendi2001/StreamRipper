from icecream import ic

from Middleware.split import Splitter, splitKey


print(splitKey(
    "BV1fS4y1X7on-30032-214012-463769"))
s = Splitter(None, None, None, None, None)
s.block_size = 256
print(s.splitRange((0, 255)))
print(s.splitRange(ic(s.getBlock(1, 255))))
print(s.splitRange(ic(s.getBlock(256, 511))))
print(s.splitRange(ic(s.getBlock(255, 512))))
print(s.splitRange(ic(s.getBlock(128, 550))))
