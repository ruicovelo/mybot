import re



class BotCommand(object):
    
    destination = None
    command = None
    arguments = None
    
    def __init__(self):
        pass

class BotCommandTranslator(object):
    '''
    Translates commands input by user into command executed by the bot
    '''
    _commands = dict()
    
    _common_commands = []               # common commands for bot controller and bot module (ex: start, stop)
    _specific_commands = []
    _destinations = []

    def __init__(self,common_commands,destinations,specific_commands):
        self._common_commands=common_commands
        self._destinations=destinations
        self._specific_commands=specific_commands
        
    def add_command(self,line,command):
        self._commands[line]=command
        
    def get_command(self,line):
        #TODO: interpret line into simple line
        if self._commands.has_key(line):
            return self._commands[line]
        return None
    
    
    def _array_to_regexp(self,array):
        s = ''
        for a in array:
            s = s + a + '|'
        return s


    def check_common_commands(self,s):
        destinations_re = self._array_to_regexp(self._destinations)
        default_commands_re = self._array_to_regexp(self._common_commands)
    
        expression = '^ *(?P<destination>' + destinations_re+ ') *' +'(?P<command>'+ default_commands_re + ') *'+ '(?P<arguments>.*) *' +'$'
        m=re.match(expression,s)
        print m.group('command')
        print m.group('destination')
        if m and m.group.has_key('command') and m.group('destination'):
            print('Match default command')
            print('destination: '+ m.group('destination'))
            print('command: '+m.group('command'))
            print('arguments: '+m.group('arguments'))
            destination = m.group('destination')
            command = m.group('command')
            arguments = m.group('arguments')
            #TODO: return something interesting
            return True
        return False
    
    def check_specific_commands(self,s):
        destinations_re = self._array_to_regexp(self._destinations)
        
        # match destination?
        expression = '^ *(?P<destination>' + destinations_re + ') *'
        m=re.match(expression,s)
        if m:
            destination = m.group('destination')
            if self._specific_commands.has_key(destination):
                commands_re = self._array_to_regexp(self._specific_commands[destination])
                expression = '^ *'+destination+' *'+'(?P<command>'+ commands_re + ') *'+ '(?P<arguments>.*) *$'
                m=re.match(expression,s)
                if m:
                    print('Match specific command')
                    print('destination: '+ destination)
                    print('command: ' + m.group('command'))
                    print ('arguments: ' + m.group('arguments'))
                    #TODO: return something interesting
                    return True
        return False       


    
    

def main():
    # demo code
    modules=['SleeperModule','ConsoleModule','MoneyModule']
    default_commands=['stop','start','shutdown','list','show']
    
    module_specific_commands={}
    module_specific_commands['ConsoleModule']=['disconnect']

    translator = BotCommandTranslator(common_commands=default_commands,destinations=modules,specific_commands=module_specific_commands)
    translator.add_command("list", "list()")
    translator.add_command("quit","break")


    
    while True:
        s = raw_input()
        if s=='':break
        # match default commands
        if translator.check_common_commands(s):
            print('Match common command')
            continue
        else:
            if translator.check_specific_commands(s):
                print('Match specific command')
                continue
        print('Unknown command')
        
        
        


if __name__ == '__main__':
    main()