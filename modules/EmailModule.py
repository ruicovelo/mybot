'''
Created on Dec 12, 2013

@author: pedro
'''
from botmodule import BotModule
from communication import email

class EmailModule(BotModule):
    '''
    Module for sending email and checking imap gmail mailbox
    '''

    def __init__(self,name='sleeper',parameters={}):
        super(EmailModule,self).__init__(name=name,parameters=parameters)
        
        
    def run(self):
        super(EmailModule,self).run()
        while not self.stopping():
            cmd = self._wait_next_command_available(3.0)
            if cmd:
                try:
                    arguments = cmd.arguments
                    exec(self._commands[cmd.name])
                except KeyError:
                    self.log.debug('Unknown command %s ' % cmd.tostring())
        self.log.debug('Exiting...')            