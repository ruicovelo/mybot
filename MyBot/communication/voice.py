'''
Created on Jul 27, 2013

@author: pedro
'''
# used for calling say or speak
import subprocess
import sys


class Voice: 
    
    _shell_command=None
    mute = False
    debug = True
    
    
    
    def __init__(self,debug=False):
        self.debug = debug
        #TODO: check availability of shell commands
        # if platform is 'darwin' I'm using my conding laptop
        if sys.platform == 'darwin':
            self._shell_command='say'
        else: #TODO: check Linux
            self._shell_command="speak"
        
        
    

    def speak(self,text):
        if not self.mute and text:
            try:
                if self.debug:
                    print self._shell_command, text
                    
                result = subprocess.call([self._shell_command,text])
                if result == 0:
                    return True
            except:
                return False