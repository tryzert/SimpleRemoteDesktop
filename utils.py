
# import zlib
from cv2 import imdecode, imencode, IMWRITE_JPEG_QUALITY, IMREAD_COLOR


def comprese_img(frame):
    # 数值越高，质量越好
    quality = 50
    return imencode('.jpg', frame, [IMWRITE_JPEG_QUALITY, quality])[1]

def decompress_img(data):
    return imdecode(data, IMREAD_COLOR)