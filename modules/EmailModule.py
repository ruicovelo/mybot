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
    smtp_server = None
    smtp_server_address = None
    smtp_username = None
    smtp_password = None #TODO: is there a better way to store credentials?

    def __init__(self,name='sleeper',parameters={}):
        super(EmailModule,self).__init__(name=name,parameters=parameters)
        self.smtp_server_address = parameters['smtp_server']
        self.smtp_username = parameters['username']
        self.smtp_password = parameters['password']
        if parameters.has_key('from_name'):
            self.smtp_from_name = parameters['from_name']
        else:
            self.smtp_from_name = self.name
        self.smtp_server = email.SMTPServer(self.smtp_server_address,self.smtp_username,self.smtp_password)
    
    def send_email(self,toaddr,subject,body):
        message = email.EmailMessage(fromaddr=self.smtp_username,toaddr=toaddr,subject=subject,body=body)
        self.smtp_server.send_single_email_message(message)
        
    def run(self):
        super(EmailModule,self).run()
        self.send_email('rui.covelo@gmail.com', 'Starting', 'Starting mail module')
        while not self.stopping():
            cmd = self._wait_next_command_available(3.0)
            if cmd:
                try:
                    arguments = cmd.arguments
                    exec(self._commands[cmd.name])
                except KeyError:
                    self.log.debug('Unknown command %s ' % cmd.tostring())
        self.log.debug('Exiting...')            