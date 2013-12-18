import logging

class MyLogger(logging.getLoggerClass()):
    '''
    Wrapper for setting up my default logging configuration
    '''
    _FORMAT = "%(asctime)s %(levelname)s: %(name)s %(message)s"

    def __init__(self,name):
        super(MyLogger,self).__init__(name)
        self._file_handlers = {}
        formatter = logging.Formatter(self._FORMAT)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.addHandler(console_handler)
        
    def add_log_file(self,filename):
        formatter = logging.Formatter(self._FORMAT)
        if filename:
            file_handler = logging.FileHandler(filename)
            file_handler.setFormatter(formatter)
            self.addHandler(file_handler)
            self._file_handlers[filename]=file_handler

    def remove_log_file(self,filename):
        #TODO: this is not working
        if self._file_handlers.has_key(filename):
            self.removeHandler(self._file_handlers[filename])
            self._file_handlers.items().remove((filename,self._file_handlers[filename]))


