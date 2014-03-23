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
 
 
        self.add_command(name='status',command='self.status()',arguments=[])
        self.add_command(name='send', command='self.send()', arguments=[('to','.+@.+'),('subject','.*'),('body','.*')])
        #self.add_command(BotCommand(destination=None,name='shutdown',command='self.shutdown()'))
        #self.add_command(BotCommand(destination=None,name='list',command='self.list_modules()'))
        #command = BotCommand(destination=None,name='start',command='self.start(arguments)')
        #command.add_argument('module', '.+')
 
        
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