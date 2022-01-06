import socketserver
import time
from threading import Thread, Lock as ThreadLock
from concurrent.futures import ThreadPoolExecutor, as_completed

from mss import mss
# from pynput import keyboard

import utils


class ImageCache:
    def __init__(self, max_cache_size=30):
        """
            图片缓存服务。udp不稳定，方便数据片段重发。
            非线程/进程安全!
        """
        self._last_frame_num = 0
        self.max_cache_size = max_cache_size
        self._cache = []
        self._frames = self._grab_screen()
        self._flag = True

    def _grab_screen(self):
        with mss() as cap:
            monitor = cap.monitors[1]
            while True:
                if self._flag:
                    frame = cap.grab(monitor)
                    # frame = tools.to_png(frame.rgb, (monitor['width'], monitor['height']))
                    # frame = utils.comprese_img(frame)
                    yield frame.rgb
                else:
                    yield None
    
    def frame(self):
        # 抓取一帧图片，更新库存，并返回最新一帧图片，
        step = utils.FRAME_SEGMENT_SIZE
        data = next(self._frames)
        if not data:
            return None, None  
        # 图片分成片段, 并进行编号.方便后续查找，以及多线程逐个发送
        segments = [data[idx:idx+step] for idx in range(0, len(data), step)]
        frame_num = int.to_bytes(self._last_frame_num, 4, 'big')
        total_step = int.to_bytes(len(segments), 4, 'big')
        for idx, seg in enumerate(segments):
            segments[idx] = frame_num + int.to_bytes(idx + 1, 4, 'big') + total_step + seg
        self._cache.append(segments)
        self._last_frame_num += 1
        if len(self._cache) > self.max_cache_size:
            self._cache.pop(0)
        return segments
    
    def segment(self, frame_num, segment_num):
        data = None
        if frame_num <= self._last_frame_num and frame_num > self._last_frame_num - len(self._cache):
            data = self._cache[frame_num - self._last_frame_num - 1][segment_num - 1]
        return data


class SingleClient:
    def __init__(self, sock, addr, timeout=30):
        self._addr = addr
        self._sock = sock
        self._timeout = timeout
        self._active_time = time.time()
    
    def __eq__(self, addr):
        return self._addr == addr
    
    def send(self, data):
        self._sock.sendto(data, self._addr)
    
    def fresh(self):
        self._active_time = time.time()
    
    @property
    def is_timeout(self):
        return time.time() - self._active_time > self._timeout
    


class ClientGroup:
    def __init__(self, max_clients_num=3):
        # self._sock = sock
        self._lock = ThreadLock()
        self._clients = [None for _ in range(max_clients_num)]
        self._executor = ThreadPoolExecutor(max_workers=max_clients_num * 7)

    def _send_segment(self, segment_data):
        # 通过多线程的方式，向每个用户发送一个图片片段
        for idx, client in enumerate(self._clients):
            if client:
                client.send(segment_data)

    def send_frame(self, frame_data):
        # 向所有客户端发送最新图片帧, frame_data是一个字节列表
        with self._lock:
            all_task = [self._executor.submit(self._send_segment, (segment_data)) for segment_data in frame_data]
            for _ in as_completed(all_task): # 没有全部发送，则会阻塞
                pass
        # 这一帧图片的完整数据，已经发送给每一个客户端。进而可以获取新一帧图片
    
    def exist(self, addr): # 只是检查客户端是否存在，其他什么也不做
        with self._lock:
            for client in self._clients:
                if client == addr:
                    return True
        return False
    
    @property
    def empty(self):
        with self._lock:
            for client in self._clients:
                if client:
                    return False
        return True
    
    @property
    def full(self):
        with self._lock:
            for client in self._clients:
                if not client:
                    return False
        return True

    def add(self, sock, addr):
        """
            1.先检查客户端是否有超时的，有的则踢出
            2.再检测用户是否存在
                1) 如果不存在，检测是否有空位置
                    i) 有空位置，则添加新客户端
                    ii) 否则不添加
                2) 如果存在, 检测其活跃时间是否超时
                    i) 未超时, 刷新活跃时间
                    ii) 超时, 将客户端清除
        
        """
        with self._lock:
            # 超时踢出
            for idx, client in enumerate(self._clients):
                if client:
                    if client.is_timeout:
                        self._clients[idx] = None
            # 检查是否重复了
            for client in self._clients:
                if client == addr:
                    client.fresh()
            # 找空位置
            for idx, client in enumerate(self._clients):
                if not client:
                    self._clients[idx] = SingleClient(sock, addr)
                    break


ICache = None #ImageCache()
CGroup = None #ClientGroup(3)


class RequestHandler(socketserver.DatagramRequestHandler):
    def handle(self):
        # 如果客户端已经存在
        if CGroup.exist(self.client_address):
            print('客户端地址已经存在', self.client_address)
            # todo: read vs readline
            data = self.rfile.readline(1024)
            frame_num = int.from_bytes(data[:4], 'big')
            segment_num = int.from_bytes(data[4:8], 'big')
            # segment = ICache.segment(frame_num, segment_num)
            # if segment:
            #     self.wfile.write(segment)
            print("数据重发")
        else: 
            # 如果客户端不存在
            print("一个新客户端请求接入: ", self.client_address, end=" ")
            if CGroup.full:
                # 拒绝服务
                print("  [info] 服务器载荷已满, 拒绝服务!")
                self.wfile.write(b'Server refused!')
            else:
                print("  [info] 接入成功! ")
                CGroup.add(self.socket, self.client_address)



class RemoteDesktopServer:
    def __init__(self, port=12345):
        """
            # 通过 addr 来鉴别不同的请求。最大请求数为3个，即最大允许3个远程客户端连接。
            # 服务端自身常驻 1-3个读线程。每进来一个连接，重新开启 n 个写线程。
            # 读: client + 1, 写: client * n
            # 如果没有，则关闭图片缓存，并关闭空闲的 读/写线程。
            改用系统库，本质是select复用
        """
        self._server = socketserver.ThreadingUDPServer(('', port), RequestHandler)
        self.run()
    
    def _update_frame(self):
        while True:
            if CGroup.empty:
                time.sleep(3)
                continue
            frame = ICache.frame()
            CGroup.send_frame(frame)

    def run(self):
        Thread(target=self._server.serve_forever, daemon=True).start()
        # Thread(target=self._update_frame, daemon=True).start()
        print("Server is running...")
        # with keyboard.Listener(on_press=lambda key: key != keyboard.Key.esc) as ltr:
        #     ltr.join()
        self._update_frame()



if __name__ == "__main__":
    ICache = ImageCache()
    CGroup = ClientGroup()
    RemoteDesktopServer()