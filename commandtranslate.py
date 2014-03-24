import re
from time import time
from collections import OrderedDict


# TODO: replace exceptions with error codes?
class BotCommandException(Exception):
    def __init__(self, message):
        self.message = message       

    def __str__(self):
        return self.message
    
class UnknownCommandException(BotCommandException):
    def __init__(self, command_name):
        self.command_name = command_name
        self.message = "Unrecognized command: %s " % command_name

class WrongValueException(BotCommandException):
    def __init__(self, argument_name):
        self.argument_name = argument_name
        self.message = "Unrecognized value for argument: %s" % argument_name

class UnknownArgumentException(BotCommandException):
    def __init__(self, argument_name):
        self.argument_name = argument_name
        self.message = "Unrecognized argument name: %s" % argument_name

class MissingValueException(BotCommandException):
    def __init__(self, argument_name):
        self.argument_name = argument_name
        self.message = "Argument '%s' requires value!" % argument_name

class MissingArgumentException(BotCommandException):
    def __init__(self, argument_name):
        self.argument_name = argument_name
        self.message = "Command requires '%s' argument! " % argument_name


class BotCommand(object):
    
    def __init__(self, name, command, arguments=None, destination_name=None,origin_name=None):
        self.destination_name = destination_name
        self.name = name
        self.command = command
        self.arguments = arguments
        self.origin_name = origin_name
        self._mandatory_arguments = OrderedDict()
        self._optional_arguments = OrderedDict()
    
    def add_argument(self, name, value_regexp=".*"):
        # TODO: optional arguments
        self._mandatory_arguments[name] = value_regexp

    def _parse_argument_list(self, arguments):
        # TODO: optional arguments
        w = 0
        new_arguments = OrderedDict()
        while w < len(arguments):
            if arguments[w] in self._mandatory_arguments.keys():
                argument_name = arguments[w]
                value_regexp = self._mandatory_arguments[argument_name]
                if value_regexp:
                    # we expect a value even if empty string
                    if w < len(arguments) - 1:
                        value = arguments[w + 1]
                        if re.match(value_regexp, value):
                            new_arguments[arguments[w]] = value
                            w = w + 2
                        else:
                            raise WrongValueException(argument_name)
                    else:
                        # we do not have a value available!
                        raise MissingValueException(argument_name)
                else:
                    # value not expected
                    new_arguments[arguments[w]] = True
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
                    if value_regexp and re.match(value_regexp, arguments[w]):
                        new_arguments[argument_name] = value
                        break
                if not new_arguments.has_key(argument_name):
                    raise UnknownArgumentException(argument_name)
                w = w + 1

        for mandatory_argument in self._mandatory_arguments.keys():
            if mandatory_argument not in new_arguments.keys():
                raise MissingArgumentException(mandatory_argument)
        return new_arguments
        
    def validate(self, arguments):
        # TODO: optional arguments
        arguments = self._parse_argument_list(arguments)
        return arguments
            
    # for debugging purposes    
    def __str__(self):
        return 'from: %s \nto: %s \nname: %s\ncommand: %s\nargs: %s' % (self.origin_name, self.destination_name, self.name, self.command, self.arguments)

class BotCommandTranslator(object):

    def __init__(self, modules, conversation_timeout_secs=10):
        self._last_current_destination_change = None
        self._current_destination = None
        self._commands = {}
        self._common_commands = {}
        self._modules = modules
        self._conversation_timeout_secs = conversation_timeout_secs
    
    def end_conversation(self):
        self._last_current_destination_change = None
        self._current_destination = None
        
    def start_conversation(self, destination):
        if self._current_destination:
            self.end_conversation()
        self._set_current_destination(destination)
        
    def _set_current_destination(self, destination):
        self._current_destination = destination
        self._last_current_destination_change = time()
        
    def _get_current_destination(self, update=True):
        '''
        Checks if current_destination is up to date and returns it.
        '''
        if update and self._last_current_destination_change:
            if (time() - self._last_current_destination_change) > self._conversation_timeout_secs :
                self.end_conversation()
            else:
                self._last_current_destination_change = time()
        return self._current_destination
    
    def get_current_destination(self, update=False):
        '''
        Gets current_destination name but does not check if it's up to date
        '''
        destination = self._get_current_destination(update)
        if destination:
            return destination
        else:
            return ''
        
    def _parse_command_line(self, command_line):
        '''
        Splits command line into "individual expressions"
        "Individual expressions" are words or sets of words inside quotes
        ''' 
        matches = re.findall(r'([0-9a-zA-Z\.@\-_\+]+)|"(.+?)"', command_line)
        words = []
        for match in matches:
            for word in match:
                if word:
                    words.append(word)
        return words
    
    def _validate_destination(self, destination_name):
        return self._modules.get_instance(destination_name)
        
    def validate_command(self, line,origin_name=None):
        '''
        Parses a command line a creates a corresponding BotCommand instance
        '''
        
        # checking if we are in a conversation
        destination = self._get_current_destination()
        
        # split into words / individual expressions 
        words = self._parse_command_line(line)
        
        #TODO: review this
        # workaround to end conversation
        # this is not a final solution and must be reviewed
        try:
            if words[0] == '.':
                self.end_conversation()
                return True
        except KeyError:
            pass
             
 
        # check if first word is a destination
        w = 0
        new_destination = self._validate_destination(words[w])
        if new_destination:  # if we have a new destination, we are sending a command directly to a destination
            destination = new_destination
            if len(words) > 1:  # skip first word because it is a destination 
                w = w + 1
            else:
                # if there is no more words, we are just starting a conversation with a destination
                self.start_conversation(destination)
                return True
        else:
            # we are in the middle of a conversation or:
            # TODO: guess destination based on command?
            pass
            
        if destination == None:  # send command to controller
            # TODO: remove this when the controller is migrated to a module ?
            return BotCommand(destination_name=None, name=words[w], command=words[w], arguments=words[w + 1:], origin_name=origin_name)
        
        # check if w word is a command accepted by the destination
        return destination.validate_command(BotCommand(destination_name=destination.name, name=words[w], command=None, arguments=words[w + 1:], origin_name=origin_name))


