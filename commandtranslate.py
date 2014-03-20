import re
from time import time
from collections import OrderedDict


class WrongValueException(Exception):
    def __str__(self):
        return "WrongValueException: unrecognized value for argument!"

class UnknownArgumentException(Exception):
    def __str__(self):
        return "UnknownArgumentException: unrecognized argument name!"

class MissingValueException(Exception):
    def __str__(self):
        return "MissingValueException: argument requires value!"


class BotCommand(object):
    
    def __init__(self,destination,name,command,arguments=None,origin=None):
        self.destination = destination
        self.name = name
        self.command = command
        self.arguments = arguments
        self.origin = origin
        self._mandatory_arguments = OrderedDict()
        self._optional_arguments = OrderedDict()
        self._arguments = OrderedDict()
    
    def add_argument(self,name,value_regexp=".*"):
        #TODO: optional arguments
        self._mandatory_arguments[name]=value_regexp

    def _parse_argument_list(self,arguments):
        #TODO: optional arguments
        w = 0
        while w < len(arguments):
            if arguments[w] in self._mandatory_arguments.keys():
                value_regexp = self._mandatory_arguments[arguments[w]]
                if value_regexp:
                    # we expect a value event if empty string
                    if w < len(arguments) - 1:
                        value = arguments[w+1]
                        if re.match(value_regexp,value):
                            self._arguments[arguments[w]]=value
                            w = w + 2
                        else:
                            raise WrongValueException()
                    else:
                        # we do not have a value available!
                        raise MissingValueException()
                else:
                    # value not expected
                    self._arguments[arguments[w]]=True
                    w = w + 1
                    continue
            else:
                # unknown argument name
                # is this a known value?
                # trying to match with the first value regexp available
                argument_name = None
                value = arguments[w]
                for argument_name in self._mandatory_arguments.keys():
                    value_regexp = self._mandatory_arguments[argument_name]
                    if value_regexp and re.match(value_regexp,arguments[w]):
                        self._arguments[argument_name]=value
                        break
                if not self._arguments.has_key(argument_name):
                    raise UnknownArgumentException()
                w = w + 1
        
    def validate(self,arguments):
        #TODO: optional arguments
        self._parse_argument_list(arguments)
        return self._arguments
            
    # for debugging purposes    
    def __str__(self):
        return 'from: %s \nto: %s \nname: %s\ncommand: %s\nargs: %s' % (self.origin,self.destination,self.name,self.command,self.arguments)

class BotCommandTranslator(object):

    def __init__(self,modules,conversation_timeout_secs=10):
        self._conversation_timeout_secs = conversation_timeout_secs
        self._last_current_destination_change = None
        self._current_destination = None
        self._commands = {}
        self._common_commands = {}
        self._modules = modules

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
        
    def _parse_command_line(self,command_line):
        '''
        Splits command line into "individual expressions"
        "Individual expressions" are words or sets of words inside quotes
        ''' 
        matches = re.findall(r'([0-9a-zA-Z\.@\-_\+]+)|"(.+)"',command_line)
        words = []
        for match in matches:
            for word in match:
                if word:
                    words.append(word)
        return words
    
    def _validate_destination(self,destination):
        return self._modules.get_instance(destination)
        
    def validate(self,line,origin=None):
        '''
        Does basic command validation and validates command destination.
        '''
        
        # checking if we are in a conversation
        destination = self._get_current_destination()
        
        # split into words / individual expressions 
        words = self._parse_command_line(line)
        if len(words) == 0:
            # could not translate into words
            # only non alphanumeric characters?
            if self._common_commands.__contains__(line) or self._commands[destination].__contains__(line):
                command = line
                return BotCommand(destination=destination,name=line,command=command,arguments=line,origin=origin)
            return False
            
        # check if first word is a destination 
        w = 0
        new_destination = self._validate_destination(words[w])
        if new_destination:
            destination = new_destination
            if len(words) > 1:
                w = w + 1
            else:
                # if there is no more words, we are just starting a conversation with a destination
                self.start_conversation(destination)
                return True
            
        if destination == None:
            # send command to controller
            #TODO: remove this when the controller is migrated to a module
            return BotCommand(destination=None,name=words[w],command=words[w],arguments=words[w+1:],origin=origin)
        
        # check if w word is a command accepted by the destination
        if self._common_commands.__contains__(words[w]):
            command = words[w]
            return BotCommand(destination=destination,name=words[w],command=command,arguments=words[w+1:],origin=origin)
        
        try:
            if self._commands[destination].__contains__(words[w]):
                command = words[w]
                return BotCommand(destination=destination,name=words[w],command=command,arguments=words[w+1:],origin=origin)
        except KeyError:
            pass
        return False


# TESTING CODE

def main():
    # demo code

    #botcommand = BotCommand(destination=None,name='send',command='send',arguments=None,origin=None)
    #botcommand.add_argument('to', '.+@.+')
    #botcommand.add_argument('subject','.+')
    #botcommand.add_argument('body','.*')
    #arguments = ['rui.covelo@gmail.com', 'subject', 'test', 'body', 'saldkl kasdlk ldalk']
    #botcommand.validate(arguments)

    translator = BotCommandTranslator()
    
    while True:
        s = raw_input().strip()
        if s=='':
            break
        cmd = translator.validate(s)
        print(cmd)
        if cmd == True:
            print('Now talking to %s ' % translator.get_current_destination())
            continue
        if cmd:
            cmd.validate(cmd.arguments)
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
