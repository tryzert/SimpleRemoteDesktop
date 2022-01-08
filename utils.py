
# import zlib
from cv2 import imdecode, imencode, IMWRITE_JPEG_QUALITY, IMREAD_COLOR


def comprese_img(frame):
    return imencode('.jpg', frame, [IMWRITE_JPEG_QUALITY, 50])[1]

def decompress_img(data):
    return imdecode(data, IMREAD_COLOR)