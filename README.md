# A simple Remote desktop Demo.
## lib dependency:
    1).Screen shot: mss
    2).Image: opencv-python
    3).Data:  numpy

First, start a server, on your command line, enter this:
    pip install -r requirements.txt
then, start a client (don't forget change your [server address] in client.py):
    python server.py
last, open another command line and enter this:
    python client.py

### Tip: You should keep your server and client in the same LAN(Local Area Network).