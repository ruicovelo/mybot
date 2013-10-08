
from time import sleep


from multiprocessing import Process

# Exchanging objects between processes
from multiprocessing import Queue

# Synchronization between processes
from multiprocessing import Lock 

# Sharing state between processes
from multiprocessing import Value
from multiprocessing import Array

from threading import Thread


# Controlling process execution
import signal
import sys


import logging

class BotModule(Process):
    '''
    This should be inherited
    TODO: force this?
    
    This should be used for creating modules, abstracting the part of managing the process that runs the module.
    Multitasking within the module should be done with threads.
    '''
    
    parameters = None               # configured startup parameters
    name = None
    
    _run = None                     # set to False to stop module as soon as it checks this value (self._stopping())
    _commands_queue = None          # queue for receiving async commands from controller    
    _commands_output_queue = None   # queue for sending commands to controller
    _output_text_queue = Queue()    # queue for receiving text from controller
    _output_queue = None            # queue to output data to controller
    _receive_output_text = False    # set to True to subscribe to receive text output to stdout
    
    # for background working while main thread receives commands i.e.
    _work_thread = None

    def __init__(self,name,parameters,log=None):
        signal.signal(signal.SIGTERM,self._forced_stop)
        if log:
            self.log = log
        else:
            self.log = logging
            
        self.name = name
        self.parameters=parameters
        self._run = Value('b',True,lock=False)
        self._commands_queue = Queue()    
        self.log.debug('Module named "%s" initiating...' % self.name)
        super(BotModule,self).__init__()
        
    def _do_work(self):
        self.log.debug('Not doing the right work...')
        pass
           
    def start(self):
        self._run.value=True
        #TODO: change Thread to MyThread (stoppable thread)
        self._work_thread = Thread(target=self._do_work)
        super(BotModule,self).start()
      
    def _forced_stop(self,signum,frame):
        self.log.debug('Stopping NOW %s ' % self.name)
        sys.exit()  
    
    def force_stop(self):
        self.terminate()
        
    # Tell module to stop as soon as possible (module has to check the _run flag)
    # This method should be overriden if the module can stop at any time with a SIGTERM signal
    # In that case call force_stop instead.
    def stop(self):
        self.log.debug('Stopping %s ...' % self.name)
        self._run.value=False
        
    def stopping(self):
        return not self._run.value
 
    def add_command(self,command,timeout=None):
        self._commands_queue.put(obj=command, block=True, timeout=timeout)
 
    def _get_command_available(self):
        command = None
        if not self._commands_queue.empty():
            command = self._commands_queue.get_nowait()
        return command
    
    def _wait_next_command_available(self,timeout=None):
        return self._commands_queue.get(True, timeout)
        
    def set_output_queue(self,q):
        self._output_queue = q
        
    def check_outputs_subscriber(self,l):
        if self._receive_output_text:
            l.append(self._output_text_queue)

    def set_commands_queue(self,q):
        self._commands_queue = q

    def set_output_commands_queue(self,q):
        self._output_commands_queue = q
        
    def output_command(self,command_line):
        if self._output_commands_queue:
            self._output_commands_queue.put(command_line)
            return True
        return False
    
    def output(self,obj):
        if self._output_queue:
            self._output_queue.put(obj)
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
   
