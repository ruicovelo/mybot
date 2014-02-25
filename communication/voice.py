# Nothing useful here yet. Just fun.
# used for calling say or speak
import subprocess
import sys


class Voice: 
    
    def __init__(self):
        self.mute = False
        #TODO: check availability of shell commands
        # if platform is 'darwin' I'm using my conding laptop
        if sys.platform == 'darwin':
            self._shell_command='say'
        else: #TODO: check Linux
            self._shell_command="speak"
        
    def speak(self,text):
        if not self.mute and text:
            try:
                result = subprocess.call([self._shell_command,text])
                if result == 0:
                    return True
            except:
                return False
