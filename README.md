# A simple Remote desktop Demo/一个远程桌面的小demo。
## lib dependency/项目依赖:
    1).Screen shot: mss / d3dshot
    2).Image: opencv-python
    3).Data:  numpy

## start a server/开启一个服务,
### 1).First, on your command line, enter this/先在命令行输入这个:
    pip install -r requirements.txt
### 2).then, start a server /然后开启一个服务端:
    python server.py
### 3).last, open another command line and enter this (don't forget change your [server address] in <u>client.py</u>)/最后运行客户端, (不要忘记修改服务端地址):
    python client.py

## Tip: You should keep your server and client in the same LAN(Local Area Network).

### todo: voice-send/recv