'''
Created on Aug 2, 2013

@author: pedro
'''

from time import sleep
from multiprocessing import Process

# Exchanging objects between processes
from multiprocessing import Queue

# Synchronization between processes
from multiprocessing import Lock 

# Sharing state between processes
from multiprocessing import Value
from multiprocessing import Array

import logging

class BotModule(object):
    '''
    This should be inherited
    TODO: force this?
    
    This should be used for creating modules, abstracting the part of managing the process that runs the module.
    Multitasking within the module should be done with threads.
    '''
    
    # this is the process that runs the code of the module
    _process = None
    _target = None
    parameters = None
    name = None
    
    # set to False to module stop as soon as it checks this value
    _run = None
    _commands_queue = None    
    _return_queue = None    
    
    _commands={}

    #TODO: still not know what I will do with this
    _siblings={}
    _introduce_queue = Queue()



    #TODO: this is still very uncomplete
    
    def __init__(self,name,parameters,log=None):
        if log:
            self.log = log
        else:
            self.log = logging
        self.name = name
        self.parameters=parameters
        self._run = Value('b',True,lock=False)
        self._commands_queue = Queue()    
        self.log.debug('Module named "%s" initiating...' % self.name)
        self._process=Process(target=self._target)
        
           
    def start(self):
        self._run.value=True
        self._process.start()
        
        
    def stop(self):
        self.log.debug('Stopping %s ' % self.name)
        self._run.value=False
    
    def join(self):
        self._process.join(timeout=None)   
 
    def add_command(self,command,timeout=None):
        self._commands_queue.put(obj=command, block=True, timeout=timeout)
 
    def _get_command_available(self):
        command = None
        if not self._commands_queue.empty():
            command = self._commands_queue.get_nowait()
        return command
    
    def _wait_next_command_available(self,timeout=None):
        return self._commands_queue.get(True, timeout)
        
    def set_return_queue(self,q):
        self._return_queue = q
        
    def output(self,obj):
        if self._return_queue:
            self._return_queue.put(obj)
            return True
        return False

    def _string_to_bool(self,s):
        try:
            if s.lower() in ['true','yes','1']:
                return True
            else:
                return False
        except AttributeError:
            return s    
   
    def is_alive(self):
        return self._process.is_alive()
   
    def pid(self):
        return self._process.pid()