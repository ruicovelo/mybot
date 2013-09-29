from threading import Thread
from threading import Event
from multiprocessing import Queue
from Queue import Empty
import socket
from os import unlink

class MyThread(Thread):  
    
    _STOP_TIMEOUT_SECS=3
    _processing_function = None
    _queue = None
    
    def __init__(self,processing_function,queue):
        super(MyThread, self).__init__()
        self._processing_function=processing_function
        self._queue = queue
        self._stop = Event()
        
    def stop(self):
        self._stop.set()
        
    def stopping(self):
        return self._stop.is_set()
        
class ReceiveQueueThread(MyThread):
    
    def run(self):
        while not self.stopping():
            try:
                s = self._queue.get(block=True, timeout=self._STOP_TIMEOUT_SECS)
            except Empty:
                continue
            if not self.stopping():
                self._processing_function(s)   

class ReceiveSocketThread(MyThread):
    
    in_socket = None
    out_socket = None

    _IN_CON_SOCKET_PATH='input_console_socket'
    _OUT_CON_SOCKET_PATH='output_console_socket'

    def stop(self):
        super(ReceiveSocketThread,self).stop()
        # hack to force thread out of accept state
        #TODO: review this
        if self.in_socket:
            temp_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            temp_socket.connect(self._IN_CON_SOCKET_PATH)
            temp_socket.close()
            

    def output_text(self,text):
        if self.out_socket:
            self.out_socket.sendall(text)
  
            
            
    
    def run(self):
        ''' queue should be set as an output queue '''

        self.in_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            unlink(self._IN_CON_SOCKET_PATH)
        except:
            pass

        self.in_socket.bind(self._IN_CON_SOCKET_PATH)
        self.in_socket.listen(0)

        while not self.stopping():
            #TODO: I probably need a better way to stop this thread. I think this might
            # lead to failed connections 
            #self.in_socket.settimeout(self._STOP_TIMEOUT_SECS)
            try:
                conn,addr=self.in_socket.accept()
            except socket.timeout:
                continue
            if not conn or self.stopping():
                break
            
            #self.in_socket.settimeout(None)
            #self.in_socket.setblocking(1)
            self.out_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            try:
                self.out_socket.connect(self._OUT_CON_SOCKET_PATH)
            except:
                self.out_socket = None
            while not self.stopping():
                data = conn.recv(1024)
                if not data:
                    break
                self._queue.put(data)
            conn.close()
            self.out_socket = None
        self.in_socket.close()
        try:
            unlink(self._IN_CON_SOCKET_PATH)
        except:
            pass
        #TODO: accept more than one connection?
            
                
                
                
# TEST CODE
def output(s):
    print(s)

def main():
    q = Queue()
    t = ReceiveSocketThread(output,q)
    s = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    try:
        import os
        os.unlink('testsocket')
    except:
        pass
    s.bind('testsocket')
    s.listen(0)
    t.in_socket=s    
    t.start()
    t.stop()
    t.join()
    s.close()
    print("Done")
    

  
if __name__ == '__main__':
    main()     