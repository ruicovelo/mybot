'''
Created on Jul 31, 2013

@author: ruicovelo

I created this for simple text messages and tested only with gmail yet. Don't expect much out of this.
'''

import imaplib2
import smtplib
import time
import re


class ValueUpdated(object):
    '''
    This classes contains values that have a validity date. Actually, a last updated timestamp.
    This might be interesting for only trying to get a new value when the one we already got is too old.
    '''
    _value = None
    updated = None
    
    def __init__(self):
        pass
    
    def set_value(self,value,time=time.time()):
        self._value = value
        self.updated = time
    
    def get_value(self):
        return self._value

class EmailMessage(object):
    
    fromaddr = None
    toaddr = None
    subject = None
    body = None
    smtp_server = None
    
    def __init__(self,fromaddr,toaddr,subject='',body='',smtp_server=None):
        self.fromaddr=fromaddr
        self.toaddr=toaddr
        self.subject=subject
        self.body=body
        self.smtp_server=smtp_server
    
    def send(self):
        self.smtp_server.send_single_message(self)
  
class SMTPServer(object):
    
    _server_address = None
    _username = None
    _password = None
    _server = None
    
    def __init__(self,server_address,username,password):
        self._server_address=server_address
        self._username=username
        self._password=password
        
    def _set_server_address(self,server_address):
        valid_port = '[0-9]+' #TODO: we can improve this
        valid_ip_port_re = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]):%s$" % valid_port
        valid_hostname_port_re = "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9]):%s$" % valid_port
        assert re.match(valid_ip_port_re,server_address) or re.match(valid_hostname_port_re,server_address), 'Invalid <server address>:<port> combination'
        self._server_address=server_address
            
    def connect(self):
        assert self._server_address, 'Server address not set correctly!'
        assert self._username and self._password, 'Credentials not set correctly!'
        self._server = smtplib.SMTP(self._server_address)
        self._server.ehlo()
        self._server.starttls()
        self._server.login(self._username,self._password)
            
    def disconnect(self):
        self._server.quit()
        
    def send_email_message(self,email_message):
        '''
        Send a simple text message.
        This wont work for more complicated stuff yet
        Server address should be on the form ip:port
        '''
        body = 'Subject: ' + email_message.subject + "\r\n" + email_message.body
        self._server.sendmail(email_message.fromaddr,email_message.toaddr,body)

    def send_single_email_message(self,email_message):
        self.connect()
        self.send_email_message(email_message)
        self.disconnect()
        
class IMAPServer(object):
    
    log = None
    server_address = None
    folder = 'INBOX'
    connection = None
    _messages = ValueUpdated()
    _new_messages = ValueUpdated()
    
    
    def get_messages_count(self,force_update=False):
        if force_update:
            self.status()
            
        return self._messages.get_value()
    
    def get_new_messages_count(self,force_update=True):
        if force_update:
            self.status()
        return self._new_messages.get_value()
    
    def get_message_ids(self):
        '''
        Returns list of message IDs as strings 
        '''
        result,data=self.connection.uid('search',None,'ALL')
        if result == 'OK':
            return data[0].split()
        
    def get_new_message_ids(self):
        '''
        Returns list of new message IDs as strings
        '''
        result,data=self.connection.uid('search',None,'UNSEEN')
        if result == 'OK':
            return data[0].split()
     
    def parse_header(self,header_data):
        '''
        For an unknown reason, I can't get HeaderParser to work properly
        '''
        result = {}
        for line in header_data:
            if ':' in line:
                name,data = line.split(':',1)
                result[name]=data
        return result
     
    def get_message_headers(self,message_ids,mark_read=False):
        search = '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])'
        if mark_read:
            '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])'
        response,data = self.connection.uid('FETCH', ','.join(map(str,message_ids)) , search)
        headers = {}
        for item in data:
            if len(item) > 1:
                msg_id = int(re.findall("[0-9]+", re.findall("\(UID [0-9]+ ", item[0])[0])[0])
                header_data = item[1].split('\r\n')
                header_data = self.parse_header(header_data)
                headers[msg_id]=header_data
        if response == 'OK':
            return headers 
    
    def status(self):
        status,response = self.connection.status('INBOX','(MESSAGES UNSEEN)')
        if status == 'OK':
            all_messages = int(re.findall("MESSAGES (\d)* ", response[0])[0])
            unseen_messages = int(re.findall("UNSEEN (\d)*\)", response[0])[0])
            self._messages.set_value(all_messages)
            self._new_messages.set_value(unseen_messages)
        else:
            return None        
       
    def select_folder(self,folder=None):
        if folder:
            self.folder = folder
        else:
            folder = self.folder
        result,data=self.connection.select(folder)
        if result == 'OK':
            self._messages.set_value(int(data[0]))
            return True
        else:
            return False
    
    def listen(self):
        '''
        Listen current folder for changes
        '''
        #TODO: timeout?
        # this thread hangs here waiting for change
        status,response = self.connection.idle()
        #TODO: what changed?
            # new emails (unread or read coming from other mailboxes)
            # email deletion / move / archive
            # NOT: email read
            # NOT: star
        if status == 'OK':
            return True
        else:
            return False
        
        
    def connect(self,username,password,server_address=None,folder=None):
        if server_address:
            self.server_address=server_address
        else:
            server_address=self.server_address
            
        #TODO: check if there is a more secure way to store passwords/credentials
        if server_address and username and password:
            self.connection=imaplib2.IMAP4_SSL(server_address)
            if self.connection:
                try:
                    result = self.connection.login(username,password)
                except imaplib2.IMAP4_SSL.error as e:
                    result = False
                finally:
                    password = None
                if result[0] == 'OK':
                    return self.select_folder(folder)
                else:
                    return False
        else:
            password = None
            self.log.debug('Not enough information to start a connection.')
            return False
            
    
    def disconnect(self):
        if self.connection:
            #TODO: learn why this has to be in this order because it just messes with  mind
            self.connection.close()
            self.connection.logout()
 
