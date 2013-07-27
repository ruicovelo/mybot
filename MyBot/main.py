'''
Created on Jul 26, 2013

@author: pedro
'''

print "Initializing bot..."
import configuration
import monitoring
from communication import voice
import networking

    


import cmd


class MyBot(object):
    '''
    classdocs
    '''
    name = "MyBot"
    _voice = voice.Voice()


    def say(self,text):
        if not self._voice.speak(text):
            print "Don't have voice?!"
  

    def __init__(self):
        '''
        Constructor
        '''
        self.say("Waking up...")
        if self.name:
            self.say("My name is " + self.name)
        else:
            self.say("Hmm... Don't know my name... Should you give me a name? That would be cool...")
            
        
    def status(self):
        print "Name: ", self.name






        
class MyBotShell(cmd.Cmd):
    prompt = "> "
    
    
    def do_status(self,line):
        bot.status()
    
    
    
    def do_quit(self,line):
        return True
    
bot=MyBot()
shell=MyBotShell()
bot.say("Waiting for your commands.")
shell.cmdloop(" ")

    