

class BotCommandTranslator(object):
    '''
    Translates commands input by user into command executed by the bot
    '''
    _commands = dict()

    def __init__(self):
        '''
        Constructor
        '''
        
    def add_command(self,line,command):
        self._commands[line]=command
        
    def get_command(self,line):
        #TODO: interpret line into simple line
        if self._commands.has_key(line):
            return self._commands[line]
        return None


def list(a):
    print("testing... testing... %s " % a)


def main():
    # demo code
    translator = BotCommandTranslator()
    translator.add_command("list", "list()")
    translator.add_command("quit","break")
    while True:
        line = raw_input()
        command = translator.get_command(line)
        if command == 'break':
            break
        if command:
            exec(command)
        
        


if __name__ == '__main__':
    main()