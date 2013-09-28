'''
Created on Jul 27, 2013

@author: pedro
'''

import logging

class MyLogging(object):
    '''
    Wrapper for the logging module
    '''
    _level = logging.DEBUG
    _filename = None
    _FORMAT = "%(asctime)s %(levelname)s %(message)s"

    def __init__(self,filename=None,level=logging.DEBUG):
        self._level = level
        self._filename = filename
        self._config()
        
    def _config(self):
        logging.basicConfig(level=self._level,format=self._FORMAT)
            
    def set_filename(self,filename):
        #TODO: check if file exists
        self._filename = filename
        self._config()
        
    def set_level(self,level):
        self._level = level
        self._config()
    
    def debug(self,msg):
        logging.debug(msg)
    def info(self,msg):
        logging.info(msg)
    def warning(self,msg):
        logging.warning(msg)
    def error(self,msg):
        logging.error(msg)
    def critical(self,msg):
        logging.critical(msg)
        
        