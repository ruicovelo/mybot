import re
from time import time



class BotCommand(object):
    
    def __init__(self,destination,name,command,arguments,origin=None):
        self.destination = destination
        self.name = name
        self.command = command
        self.arguments = arguments
        self.origin = origin

    # for debugging purposes    
    def __str__(self):
        return 'from: %s \nto: %s \nname: %s\ncommand: %s\nargs: %s' % (self.origin,self.destination,self.name,self.command,self.arguments)

class BotCommandTranslator(object):

    def __init__(self,conversation_timeout_secs=10):
        self._conversation_timeout_secs = conversation_timeout_secs
        self._last_current_destination_change = None
        self._current_destination = None
        self._commands = {}
        self._common_commands = {}

    def add_command(self,destination_name,command_name):
        '''
        Add a command to our dictionary of commands
        '''
        if not self._commands.has_key(destination_name):
            self._commands[destination_name]=[]
        self._commands[destination_name].append(command_name)
        
    def add_commands(self,destination_name,commands):
        '''
        Add a list of commands one by one
        '''
        for command_name in commands:
            self.add_command(destination_name, command_name)
        
    def remove_destination(self,destination_name):
        try:
            self._destinations.remove(destination_name)
            if self._current_destination == destination_name:
                self._current_destination = None
                self._last_current_destination_change = None
        except ValueError:
            pass
    
    def end_conversation(self):
        self._last_current_destination_change = None
        self._current_destination = None
        
    def start_conversation(self,destination):
        if self._current_destination:
            self.end_conversation()
        self._set_current_destination(destination)
        
    def _set_current_destination(self,destination):
        self._current_destination = destination
        self._last_current_destination_change = time()
        
    def _get_current_destination(self,update=True):
        '''
        Checks if current_destination is up to date and returns it.
        '''
        if update and self._last_current_destination_change:
            if (time() - self._last_current_destination_change) > self._conversation_timeout_secs :
                self.end_conversation()
            else:
                self._last_current_destination_change = time()
        return self._current_destination
    
    def get_current_destination(self,update=False):
        '''
        Gets current_destination name but does not check if it's up to date
        '''
        destination = self._get_current_destination(update)
        if destination:
            return destination
        else:
            return ''

    def validate(self,line,origin=None):
        destination = self._get_current_destination()
        
        # split into words 
        words = re.findall(r"[\w]+",line)
        print(words)
        if len(words) == 0:
            # could not translate into words
            # only non alphanumeric characters?
            if self._common_commands.__contains__(line) or self._commands[destination].__contains__(line):
                command = line
                return BotCommand(destination=destination,name=line,command=command,arguments=line,origin=origin)
            return False
            
        # check if first word is a destination 
        w = 0
        if self._commands.keys().__contains__(words[w]):
            destination = words[0]
            if len(words) > 1:
                w = w + 1
            else:
                self.start_conversation(destination)
                return True
            
        # check if w word is a command accepted by the destination
        if self._common_commands.__contains__(words[w]):
            command = words[w]
            return BotCommand(destination=destination,name=words[w],command=command,arguments=words[w+1:],origin=origin)
        
        if self._commands[destination].__contains__(words[w]):
            command = words[w]
            return BotCommand(destination=destination,name=words[w],command=command,arguments=words[w+1:],origin=origin)
        return False


# TESTING CODE

def stop(arguments):
    print('stopping')

def start(arguments):
    print('starting')

def end_conversation(arguments):
    print('end conversation')


def main():
    # demo code
    modules=[None,'sleeper','console','money','mail']
    #common_commands=['stop','start','status',('ok','bye','.'),'?']
    common_commands={'stop': stop,'start': start,'.':end_conversation}
    module_specific_commands={}

    #for module in modules:
    #    module_specific_commands[module]=[]   
    #module_specific_commands['console'].append('disconnect')
    translator = BotCommandTranslator()
    
    for module in modules:
        for common_command in common_commands.keys():
            translator.add_command(destination_name=module, command_name=common_command) # , command=common_commands[common_command])
        
    #for module in modules:    
    #    translator.add_commands(module,module_specific_commands[module])
    
    while True:
        s = raw_input().strip()
        if s=='':
            break
        cmd = translator.validate(s)
        if cmd == True:
            print('Now talking to %s ' % translator.get_current_destination())
            continue
        if cmd:
 
            print(cmd)
            if cmd.command in ['ok','bye','.']:
                print('%s: Bye!' % translator.get_current_destination())
                translator.end_conversation()
                continue
            if cmd.command in ['?']:
                print('%s: yes...' % translator.get_current_destination())
                continue
            print(cmd)
        else:
            print('%s: not sure what that means...' % translator.get_current_destination())

        
if __name__ == '__main__':
    main()
