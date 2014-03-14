'''
Created on Dec 10, 2013

@author: ruicovelo
'''
from botmodule import BotModule
import mymoney
import time

class MymoneyModule(BotModule):
    '''
    Access bank account information
    '''

    def __init__(self,name='bank',parameters={}):
        super(MymoneyModule,self).__init__(name=name,parameters=parameters)
        try:
            self._period_minutes = 1 
            self._last_check = None
            self._username = parameters['username']
            self._password = parameters['password']
            self._account_number = parameters['account']
        except KeyError, e:
            self.log.error('Invalid configuration: ' + str(e))
        try:
            self._period_minutes = parameters['minutes']
        except KeyError, e:
            self.log.debug('Going with default values')
 

    def get_transactions(self):
        if not self._username or not self._password or not self._account_number:
            self.log.error('Invalid configuration!')
            return None
        try:
            self.log.info('Getting transactions...')
            bank = mymoney.BPINet({"user": self._username, "pass": self._password})
            account = bank.get_account(self._account_number)  
            transactions=account.get_movements()
            self._last_check = time.time()
            return transactions
        except Exception, e:
            self.log.error(str(e))
            
    def run(self):
        super(MymoneyModule,self).run()
        
        while not self.stopping():
            command = self._wait_next_command_available(10.0)
            if command:
                #TODO: execute_command
                pass
            else:
                if not self.stopping():
                    if self._period_minutes > 0 and (not self._last_check or (time.time() - self._last_check)/60 > self._period_minutes):
                        transactions = self.get_transactions()
                        if transactions:
                            for transaction in transactions:
                                self.log.debug(transaction.to_string())
                            #TODO: do something to transactions
                        else:
                            self.log.error('Could not get transactions!')