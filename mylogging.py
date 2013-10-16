import logging

class MyLogger(logging.getLoggerClass()):
    '''
    Wrapper for setting up my default logging configuration
    '''
    _FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

    def __init__(self,name):
        super(MyLogger,self).__init__(name)
        formatter = logging.Formatter(self._FORMAT)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.addHandler(console_handler)
        
    def set_log_file(self,filename):
        formatter = logging.Formatter(self._FORMAT)
        if filename:
            file_handler = logging.FileHandler(filename)
            file_handler.setFormatter(formatter)
            self.addHandler(file_handler)
