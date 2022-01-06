from threading import Thread
from time import sleep
import socket
from queue import Queue

import utils
# from pynput import keyboard
import cv2 as cv
import numpy as np


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
        buf_size = utils.RESPONSE_BUF_SIZE
        while True:
            data, addr = self.sock.recvfrom(buf_size)
            if data == b'Server refused!':
                print("服务器已经满负荷，稍后会尝试重连...点击空格退出...")
                break
            if addr != self.server_addr:
                continue
            frame_num = int.from_bytes(data[:4], 'big')
            step = int.from_bytes(data[4:8], 'big')
            total_step = int.from_bytes(data[8:12], 'big')
            data = data[12:]
            self._q.put((frame_num, step, total_step, data))
            # print(frame_num, step, total_step, len(data))
    
    def _merge_img(self):
        f_num = -1 
        space_holder = int.to_bytes(0, 50 * 1024, 'big')
        frames = [space_holder for _ in range(122)]
        frames[-1] = int.to_bytes(0, 25600, 'big')
        while True:
            frame_num, step, total_step, data = self._q.get()
            if frame_num > f_num:
                # 合并
                yield frame_num, b''.join(frames)
                f_num = frame_num
            else:
                frames[step - 1] = data
    
    def _show_img(self):
        frq = cv.getTickFrequency()
        tick = cv.getTickCount()
        fps = 0
        while True:
            frame_num, frame = next(self._gen)
            if not frame:
                continue 
            
            img = np.frombuffer(frame, np.uint8)
            img = np.reshape(img, (1080, 1920, 3))
            img = cv.resize(img, (int(.45 * 1920), int(.45 * 1080)))
            img = cv.cvtColor(img, cv.COLOR_RGB2BGR)
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
        self._send_data(int.to_bytes(0, utils.REQUEST_BUF_SIZE, 'big'))
        for _ in range(recv_thread_num):
            Thread(target=self._recv_data, daemon=True).start()
        Thread(target=self._show_img, daemon=True).start()
        # with keyboard.Listener(on_press=lambda x: x != keyboard.Key.space) as ltr:
        #     ltr.join()
        while True:
            sleep(10)


if __name__ == "__main__":
    RemoteDesktopClient(show_frame=False)