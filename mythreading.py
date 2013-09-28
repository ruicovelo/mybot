from threading import Thread
from threading import Event
from multiprocessing import Queue
from Queue import Empty

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
        
class ReceiveThread(MyThread):
    
    def run(self):
        while not self.stopping():
            try:
                s = self._queue.get(block=True, timeout=self._STOP_TIMEOUT_SECS)
            except Empty:
                continue
            if not self.stopping():
                self._processing_function(s)   



# TEST CODE
def output(s):
    print(s)

def main():
    q = Queue()
    t = ReceiveOutputsThread(output,q)
    t.start()
    q.put('test')
    while not q.empty():
        pass
    t.stop()
    t.join()
    print("Done")
    

  
if __name__ == '__main__':
    main()     