'''
Created on Jul 31, 2013

@author: pedro
'''

import logging
import imaplib2
import time


class ValueUpdated(object):
    '''
    This classes contains values that have a validaty date. Actually, a last updated timestamp.
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

class MyEmailMessage(object):
    
    def __init__(self):
        pass

class MyIMAPEmail(object):
    
    log = None
    server_address = None
    folder = 'INBOX'
    connection = None
    _messages = ValueUpdated()
    _new_messages = ValueUpdated()
    
    
    def get_messages_count(self,force_update=False):
        if force_update:
            self.select_folder(self.folder)
        return self._messages.get_value()
    
    def get_new_messages_count(self,force_update=False):
        pass
    def __init__(self,log=None):
        if log:
            self.log = log
        else:
            self.log = logging
        self.log.debug('Created MyEmail instance')
        
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
        self.log.debug('Something changed:')
        self.log.debug(status)
        self.log.debug(response)
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
                self.log.debug("Connection accepted")
                try:
                    result,data = self.connection.login(username,password)
                except imaplib2.IMAP4_SSL.error as e:
                    self.log.debug(str(e))
                    result = False
                finally:
                    password = None
                if result == 'OK':
                    self.log.debug("Login OK")
                    return self.select_folder(folder)
                else:
                    return False
        else:
            password = None
            self.log.debug('Not enough information to start a connection.')
            return False
            
    
    def disconnect(self):
        if self.connection:
            #TODO: learn why this has to be in this order because it just messes with my mind
            self.connection.close()
            self.connection.logout()
    