from pathlib import Path
import configparser

"""
    服务端发送/客户端接收的消息格式
        [图片帧编号 4bytes] + [图片数据的字节数 4bytes]
         + [图片片段编号 4bytes] + [总片段数: 4bytes]
         + [图片片段数据: 1024 * 40bytes]
    服务端接收/客户端发送的消息格式 
        [图片帧编号 4bytes] + [图片片段编号 4bytes]
"""


def load_config():
    cfp  = configparser.ConfigParser()
    config_file_path = "config.ini"
    config_file = Path(config_file_path)
    if config_file.exists() and config_file.is_file():
        cfp.read(config_file_path)
    else:
        frame_segment_size = 1024 * 50
        cfp["Server"] = {
            "port": 12345,
            "recv_data_length": 4 + 4,
            "frame_segment_size": frame_segment_size,
            "send_data_length": frame_segment_size + 4 + 4 + 4 + 4,
            "client_timeout": 10, # seconds. Close client after client timeout
            "image_cache_size": 10
        }
        cfp["Client"] = {
            "recv_data_length": frame_segment_size + 4 + 4 + 4 + 4,
            "send_data_length": 4 + 4,
            "server_timeout": 10 # sendoncs. Close itself when don"t recv-data from server after a duration.
        }
        with open("config.ini", "w") as f:
            cfp.write(f)
    return cfp


# 获取服务端配置
class ServerConfig:
    def __init__(self):
        self._cfg = load_config()

    def get(self, opt):
        return self._cfg.get("Server", opt)

    def getint(self, opt):
        return self._cfg.getint("Server", opt)


# 获取客户端配置
class ClientConfig:
    def __init__(self):
        self._cfg = load_config()
    
    def get(self, opt):
        return self._cfg.get("Client", opt)
    
    def getint(self, opt):
        return self._cfg.getint("Client", opt)
