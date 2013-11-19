import re
from time import time



class BotCommand(object):
    
    origin = None
    destination = None
    command = None
    arguments = []
    
    def __init__(self,destination,command,arguments,origin=None):
        self.destination = destination
        self.command = command
        self.arguments = arguments
        self.origin = origin

    # for debugging purposes    
    def tostring(self):
        return 'from: %s \nto: %s \ncommand: %s\nargs: %s' % (self.origin,self.destination,self.command,self.arguments)


class BotCommandTranslator(object):
    
    _destinations = []
    _commands = {}
    _current_destination = None
    _last_current_destination_change = None
    _conversation_timeout_secs = 10           # seconds
    
    def __init__(self,destinations,commands,conversation_timeout_secs=10):
        self._destinations=destinations
        self._commands = commands
        self._conversation_timeout_secs = conversation_timeout_secs
    
    def _set_current_destination(self,destination):
        self._current_destination = destination
        self._last_current_destination_change = time()
        
    def _get_current_destination(self):
        if self._last_current_destination_change:
            if (time() - self._last_current_destination_change) > self._conversation_timeout_secs :
                self._last_current_destination_change = None
                self._current_destination = None
            else:
                self._last_current_destination_change = time()
        return self._current_destination
    
    def validate(self,line,origin=None):
        destination = self._get_current_destination()
        # split into words 
        #TODO: test with special characters
        words = re.findall(r"[\w]+",line)
        
        # check if first word is a destination 
        w = 0
        if self._destinations.__contains__(words[w]):
            destination = words[0]
            if len(words) > 1:
                w = w + 1
            else:
                self._set_current_destination(destination)
                return True
            
        # check if w word is a command accepted by the destination
        if self._commands[destination].__contains__(words[w]):
            command = words[w]
            return BotCommand(destination,command,words[w+1:],origin)
        return False


def main():
    # demo code
    modules=[None,'sleeper','console','money']
    default_commands=['stop','start','shutdown','list','show']
    
    module_specific_commands={}
    
    for module in modules:
        module_specific_commands[module]=[]
        for default_command in default_commands:
            module_specific_commands[module].append(default_command)
    
    module_specific_commands['console'].append('disconnect')
    translator = BotCommandTranslator(modules,module_specific_commands)
    
    while True:
        s = raw_input().strip()
        if s=='':break
        cmd = translator.validate(s)
        if cmd == True:
            continue
        if cmd:
            print(cmd.tostring())
        
        


if __name__ == '__main__':
    main()
