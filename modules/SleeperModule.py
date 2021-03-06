'''
Created on Aug 8, 2013


This is a test module. All it does is sleep and spit out something 
@author: pedro
'''

from botmodule import BotModule
from time import sleep
import random


class SleeperModule(BotModule):

    _default_args = {'seconds':5,'randomize':False}
    
    def __init__(self,name='sleeper',parameters={}):
        super(SleeperModule,self).__init__(name=name,parameters=parameters)
        for arg in self._default_args:
            if not self.parameters.has_key(arg):
                self.parameters[arg] = self._default_args[arg]    
        self._seconds = int(self.parameters['seconds']) 
        self._randomize = self._string_to_bool(self.parameters['randomize'])
        if self._randomize:
            random.seed()
    
    def run(self):
        super(SleeperModule,self).run()
        # run until module is terminated
        while self._run.value:
            if self._randomize:
                seconds = random.randint(1,self._seconds)
            else:
                seconds = self._seconds
            self.output('%s sleeping %d seconds...' % (self.name,seconds))
            
            sleep(seconds)
            command = self._get_command_available()
            if command:
                print(command)
                
            
            
    
        
    
    
    
    
