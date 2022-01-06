
"""
    服务端发送/客户端接收的消息格式
        [图片帧编号 4bytes] + [图片片段编号 4bytes] + [总片段数: 4bytes]  + [图片片段数据: 1024 * 40bytes]
    服务端接收/客户端发送的消息格式 
        [图片帧编号 4bytes] + [图片片段编号 4bytes]
"""

import zlib


FRAME_SEGMENT_SIZE = 1024 * 50 # bytes

RESPONSE_BUF_SIZE = 4 + 4 + 4 + FRAME_SEGMENT_SIZE # bytes
REQUEST_BUF_SIZE = 4 + 4 # bytes

def comprese_img(data):
    # return zlib.compress(data, 0)
    return data

def decompress_img(data):
    # return zlib.decompress(data)
    return data