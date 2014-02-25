import logging

class MyLogger(logging.getLoggerClass()):
    '''
    Wrapper for setting up my default logging configuration
    '''
    _FORMAT = "%(asctime)s %(levelname)s: %(name)s %(message)s"

    def __init__(self,name):
        super(MyLogger,self).__init__(name)
        self._formatter = logging.Formatter(self._FORMAT)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self._formatter)
        self.addHandler(console_handler)
        
    def add_log_file(self,filename):
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(self._formatter)
        self.addHandler(file_handler)
        
    def add_log_queue(self,queue):
        queue_handler = QueueHandler(queue)
        queue_handler.setFormatter(self._formatter)
        self.addHandler(queue_handler)
        
class QueueHandler(logging.Handler):
    
    def __init__(self,queue):
        super(QueueHandler,self).__init__()
        self.queue = queue
    
    def emit(self,record):
        msg = self.format(record)
        self.queue.put(msg)
