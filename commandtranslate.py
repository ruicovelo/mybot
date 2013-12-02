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
    
    _common_commands={}                     # commands accepted by all modules / destinations
    _commands = {}
    _current_destination = None
    _last_current_destination_change = None
    _conversation_timeout_secs = 10           # seconds
    
    def __init__(self,common_commands={},conversation_timeout_secs=10):
        self._common_commands=common_commands
        self._conversation_timeout_secs = conversation_timeout_secs

    def add_commands(self,module_name,commands):
        if not self._commands.has_key(module_name):
            self._commands[module_name]=[]    
        self._commands[module_name].extend(commands)
        
    def remove_destination(self,destination_name):
        try:
            self._destinations.remove(destination_name)
            if self._current_destination == destination_name:
                self._current_destination = None
                self._last_current_destination_change = None
        except ValueError:
            pass
    
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
        if self._commands.keys().__contains__(words[w]):
            destination = words[0]
            if len(words) > 1:
                w = w + 1
            else:
                self._set_current_destination(destination)
                return True
            
        # check if w word is a command accepted by the destination
        if self._common_commands.__contains__(words[w]) or self._commands[destination].__contains__(words[w]):
            command = words[w]
            return BotCommand(destination,command,words[w+1:],origin)
        return False


def main():
    # demo code
    modules=[None,'sleeper','console','money']
    common_commands=['stop','start','status']
    module_specific_commands={}

    for module in modules:
        module_specific_commands[module]=[]   
    module_specific_commands['console'].append('disconnect')
    translator = BotCommandTranslator(common_commands)
    
    for module in modules:    
        translator.add_commands(module,module_specific_commands[module])
    
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
