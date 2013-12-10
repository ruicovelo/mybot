'''
Created on Dec 10, 2013

@author: ruicovelo
'''
from botmodule import BotModule
import mymoney

class MymoneyModule(BotModule):
    '''
    Access bank account information
    '''
    
    _username = None
    _password = None
    _account_number = None

    def __init__(self,name='bank',parameters={}):
        '''
        Constructor
        '''
        super(MymoneyModule,self).__init__(name=name,parameters=parameters)
 

    def get_transactions(self):
        bank = mymoney.BPINet({"user": self._username, "pass": self._password})
        try:
            #accounts = bank.get_account_list()
            account = bank.get_account(self._account_number)  
            transactions=account.get_movements()
            for transaction in transactions:
                print("%s\t%s\t%s" % (transaction.date,transaction.description,transaction.value))
        except Exception, e:
            print(e)