from threading import Thread
from threading import Event
from multiprocessing import Queue
from Queue import Empty
import socket
import logging

class MyThread(Thread):  
    
    STOP_TIMEOUT_SECS=10.0
    _processing_function = None
    _queue = None
    
    def __init__(self,processing_function):
        super(MyThread, self).__init__()
        self._processing_function=processing_function
        self._stop = Event()
        
    def stop(self):
        self._stop.set()
        
    def stopping(self):
        return self._stop.is_set()
        
class ReceiveQueueThread(MyThread):
    
    def __init__(self,processing_function,queue):
        super(ReceiveQueueThread,self).__init__(processing_function)
        self._queue = queue

    def run(self):
        while not self.stopping():
            try:
                s = self._queue.get(block=True, timeout=self.STOP_TIMEOUT_SECS)
            except Empty:
                continue
            if not self.stopping():
                self._processing_function(s)

class ReceiveSocketThread(MyThread):

    def __init__(self,processing_function,connection):
        super(ReceiveSocketThread,self).__init__(processing_function)
        self._connection = connection
            
    def run(self):
        #TODO: set connection timeout ?
        while not self.stopping():
            data = self._connection.recv(1024)
            if not data:
                break
            if not self.stopping():
                self._processing_function(data)
                            
                

def main():
    pass                

  
if __name__ == '__main__':
    main()     