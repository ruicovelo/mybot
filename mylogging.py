import logging

class MyLogger(logging.getLoggerClass()):
    '''
    Wrapper for setting up my default logging configuration
    '''
    _FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

    _file_handlers = {}

    def __init__(self,name):
        super(MyLogger,self).__init__(name)
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

# DEBUG and sample code
if __name__ == '__main__':
    class test(object):
        def __init__(self,name):
            self.log = logging.getLogger(name)
            self.log.setLevel(logging.DEBUG)
            self.tlog()

        def tlog(self,message=''):
            self.log.debug('test: %s ' % message)

    logging.setLoggerClass(MyLogger)
    a = test('a')
    b = test('b')
    l = logging.getLogger('a')
    l.add_log_file('a.log')
    l.add_log_file('common.log')
    l = logging.getLogger('b')
    l.add_log_file('b.log')
    l.add_log_file('common.log')
    a.tlog('should be in a.log and in common.log')
    b.tlog('should be in b.log and in common.log')
    logging.getLogger('a').remove_log_file('common.log')
    a.tlog('should NOT be in common.log')
    b.tlog('should be in common.log')
    logging.shutdown()

