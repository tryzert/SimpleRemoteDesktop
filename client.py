from threading import Thread
from time import sleep
import socket
from queue import Queue

import cv2 as cv
import numpy as np

from config import ClientConfig
from utils import decompress_img


_cfg = ClientConfig()

class RemoteDesktopClient:
    """
        客户端抽象，包含一个写数据线程和若干读数据线程
        id 是 客户端身份标识，从服务端获取。因为要多线程从服务端读取数据
    """
    def __init__(self, show_frame=True, show_fps=True, server_addr=('127.0.0.1', 12345), recv_thread_num=10, send_thread_num=3):
        self.server_addr = server_addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._q = Queue(50 * 30)
        self._gen = self._merge_img()
        self.show_frame = show_frame
        self.show_fps = show_fps
        self._run(recv_thread_num)

    def _send_data(self, data):
        self.sock.sendto(data, self.server_addr)
    
    def _recv_data(self):
        buf_size = _cfg.getint('recv_data_length')
        while True:
            data, addr = self.sock.recvfrom(buf_size)
            if data == b'Server refused!':
                print("服务器已经满负荷，稍后会尝试重连...点击空格退出...")
                break
            if addr != self.server_addr:
                continue
            frame_num = int.from_bytes(data[:4], 'big')
            frame_length = int.from_bytes(data[4:8], 'big')
            step = int.from_bytes(data[8:12], 'big')
            total_step = int.from_bytes(data[12:16], 'big')
            data = data[16:]
            self._q.put((frame_num, frame_length, step, total_step, data))
    
    def _merge_img(self):
            frame_num, frame_length, step, total_step, data = self._q.get()
            _num = frame_num
            _length = frame_length
            segments = [None for _ in range(total_step)]
            segments[step - 1] = data
            while True:
                frame_num, frame_length, step, total_step, data = self._q.get()
                if frame_num > _num:
                    # 新的一帧过来了,返回上一帧, 如果丢包了，则丢弃这一帧
                    frame_bytes = b''.join(segments)
                    if all(segments) and  len(frame_bytes) == _length:
                        yield frame_num, frame_bytes
                    else:
                        yield None, None
                    segments = [None for _ in range(total_step)]
                    _num = frame_num
                    _length = frame_length
                segments[step - 1] = data
    
    def _show_img(self):
        frq = cv.getTickFrequency()
        tick = cv.getTickCount()
        fps = 0
        while True:
            frame_num, frame = next(self._gen)
            if not frame:
                continue
            img = np.frombuffer(frame, np.uint8)
            img = decompress_img(img)
            img = np.reshape(img, (1080, 1920, 3))
            img = cv.resize(img, (int(.45 * 1920), int(.45 * 1080)))
            if self.show_frame:
                img = cv.putText(img, 'Frame: {}'.format(frame_num), (10, 20), cv.FONT_HERSHEY_SIMPLEX, .7, (0,0,255), 2)
            if self.show_fps:
                tmp_tick = cv.getTickCount()
                tmp_fps = frq / (tmp_tick - tick)
                if abs(fps - tmp_fps) > 5:
                    fps = tmp_fps
                tick = tmp_tick
                if self.show_frame:
                    img = cv.putText(img, 'Fps: {:.1f}'.format(fps), (10, 50), cv.FONT_HERSHEY_SIMPLEX, .7, (0,0,255), 2)
                else:
                    img = cv.putText(img, 'Fps: {:.1f}'.format(fps), (10, 20), cv.FONT_HERSHEY_SIMPLEX, .7, (0,0,255), 2)
            cv.imshow("img", img)
            cv.waitKey(1)

    def _run(self, recv_thread_num):
        self._send_data(int.to_bytes(0, _cfg.getint('send_data_length'), 'big'))
        for _ in range(recv_thread_num):
            Thread(target=self._recv_data, daemon=True).start()
        Thread(target=self._show_img, daemon=True).start()
        while True:
            sleep(10)


if __name__ == "__main__":
    RemoteDesktopClient()