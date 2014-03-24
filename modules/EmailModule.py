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
        
        self.add_command(name='send', command='send', arguments=[('to','.+@.+'),('subject','.*'),('body','.*')])

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
        try:
            self.smtp_server.send_single_email_message(message)
        except Exception,e:
            self.output(str(e))
            return False
        else:
            return True
         
    def send(self,arguments):
        if self.send_email(arguments['to'], arguments['subject'], arguments['body']):
            self.output('Email message has been sent.')
        else:
            self.output('Failed sending email message!')
 
    def run(self):
        super(EmailModule,self).run()
        while not self.stopping():
            cmd = self._wait_next_command_available(3.0)
            if cmd:
                if self._execute(cmd):
                    self.log.debug('Command executed correctly.')
                else:
                    self.log.debug('Error occurred')
        self.log.debug('Exiting...')            
