import sys
import os
import re
import logging
import cmd  #TODO: lose this
import imp                              # loading modules
from glob import glob                   # file system walking
from ConfigParser import ConfigParser   
from multiprocessing import Queue
from threading import Thread
import mythreading


# My modules
from communication import voice
from commandtranslate import BotCommandTranslator

class MyBot(object):
    name = "MyBot"
    _voice = voice.Voice()
    
    _MODULE_PATH='modules/'
    _loaded_modules=[]
    _runnable_modules={}
    _outputs = Queue()
    _commands = Queue()

    
    translator = None
    
    _shuttingdown = False
    
    _THREAD_TIMEOUT_SECS = 5.0
    _console_receive_thread = None
    _receive_commands_thread = None
    _receive_outputs_thread = None
    
    # COMMANDS
    
    def shutdown(self):
        self._shuttingdown = True
        self.output_text('Shutting down...')
        #TODO: send shutdown to connected consoles ?
        
        # Shutting down modules
        for rm in self.get_runnable_modules():
            self.stop_module(rm[0])
        #TODO: join
        
        if self._console_receive_thread:
            logging.debug('Closing console receive thread...')
            self._console_receive_thread.stop()

        if self._receive_commands_thread:
            logging.debug('Closing receive commands thread')
            self._receive_commands_thread.stop()
 
        if self._receive_outputs_thread:
            logging.debug('Closing receive outputs thread')
            self._receive_outputs_thread.stop()
 
 
        self._console_receive_thread.join(15.0)
        self._receive_outputs_thread.join(self._THREAD_TIMEOUT_SECS)
        self._receive_commands_thread.join(self._THREAD_TIMEOUT_SECS)   
 
        #TODO: not sure if this is necessary
        if self._receive_outputs_thread.is_alive():
            logging.error('Receive outputs thread is taking too long to close...')
   
        if self._receive_commands_thread.is_alive():
            logging.error('Receive commands thread is taking too long to close...')
        
        if self._console_receive_thread.is_alive():
            logging.error('Receive consoles thread is taking too long to close...') 
            
    def get_available_modules_files(self):
        modules_list = []
        all_files = glob(self._MODULE_PATH+"/*.py")
        logging.debug(all_files)
        module_name_reg=re.compile('[A-Z][a-z0-9]*Module.py')
        for file_path in all_files:
            filename = os.path.basename(file_path)
            if module_name_reg.match(filename):
                modules_list.append(file_path)
        return modules_list

    def get_runnable_modules(self):
        runnable_modules = []
        for runnable_module in self._runnable_modules.keys():
            runnable_modules.append((runnable_module,self._runnable_modules[runnable_module].is_alive()))
        return runnable_modules

    def list_modules(self):
        runnable_modules = self.get_runnable_modules()
        self.output_text('Available modules:')
        for rm in runnable_modules:
            if rm[1]:
                status = 'Running'
            else:
                status = 'Stopped'
            self.output_text("%s\t%s" % (rm[0],status))
            
    def load_modules(self):
        logging.debug('load_modules')
        available_modules_files = self.get_available_modules_files()
        for file_path in available_modules_files:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            logging.info("Importing module '%s' from %s" % (module_name,file_path))
            try:
                loaded_module = imp.load_source(module_name,file_path)
                self._loaded_modules.append(loaded_module)
            except Exception as e:
                logging.error('Unable to load module!')
                logging.error(str(type(e)) + e.message)

    def launch_module(self,loaded_module):
        config_parser = ConfigParser()
        config_file_path = os.path.join(self._MODULE_PATH+loaded_module.__name__+'.cfg')
        initialization_values = {}
        self._configuration_defaults={'Instances': 1,'Run': True}

        
        logging.debug("Loading configuration file %s ..." % config_file_path)
        config_parser.read(config_file_path)

        if not config_parser.has_section('Initialization'):
            config_parser.add_section('Initialization')
            
        for default in self._configuration_defaults:
            if config_parser.has_option('Initialization', default):
                initialization_values[default] = config_parser.get('Initialization', default)
            else:
                initialization_values[default] = self._configuration_defaults[default]
                config_parser.set('Initialization', default, self._configuration_defaults[default])
        
        config_parser.write(open(config_file_path,"w"))
        
        for i in range(1,int(initialization_values['Instances'])+1):
            configuration_values = {}
            
            # searching for specific Instance configuration values
            if config_parser._sections.has_key('Instance ' + str(i)):
                logging.debug('Loading specific configuration values for %s ...' % 'Instance ' + str(i))
                # loading specific Instance configuration values
                for option in config_parser._sections['Instance ' + str(i)].keys():
                    configuration_values[option]=config_parser._sections['Instance ' + str(i)][option]
                # adding common values do Instance configuration that were not specified 
                for option in initialization_values.keys():
                    if not configuration_values.has_key(option):
                        configuration_values[option]=initialization_values[option]
            else:
                # not specific section found
                # loading common option
                logging.debug('Loading common configuration values...')
                for option in initialization_values.keys():
                    configuration_values[option]=initialization_values[option]
            
            new_module = None
            new_module_name = None
            if configuration_values.has_key('name'):
                new_module_name = configuration_values['name']
            else:
                new_module_name = loaded_module.__name__
            n = 1
            while self._runnable_modules.has_key(new_module_name):
                new_module_name = loaded_module.__name__ + str(n)
                n = n + 1
                
            exec('new_module = loaded_module.%s(name=new_module_name,parameters=configuration_values)' % (loaded_module.__name__))
            new_module.set_return_queue(self._outputs)
            self._runnable_modules[new_module.name]=new_module
            if configuration_values['Run'] == 'True':
                new_module.start()

    def stop_module(self,module_name):
        if not self._runnable_modules.has_key(module_name):
            self.output_text('Module ''%s'' not found!' % module_name)
            return False
        loaded_module = self._runnable_modules[module_name]
        loaded_module.stop()
        return True
    
    def say(self,text):
        #TODO: move this to a module
        if not self._voice.speak(text):
            print("Don't have voice?!")
  
    def status(self):
        self.output_text("Name: %s" % self.name)
  
    # EO COMMANDS /
    
    def __init__(self):
        logging.debug('Initializing MyBot...')
        
        # Loading acceptable commands
        self.translator = BotCommandTranslator()
        self.translator.add_command("list", "list_modules()")
        
        self._receive_commands_thread = mythreading.ReceiveQueueThread(self.execute_command,self._commands)
        self._receive_commands_thread.start()
        
        self._receive_outputs_thread = mythreading.ReceiveQueueThread(self.output_text,self._outputs)
        self._receive_outputs_thread.start()
        
        # Loading modules
        self.load_modules()
        for loaded_module in self._loaded_modules:
            self.launch_module(loaded_module)
            
        
                
    def output_text(self,text):
        ''' Handle the output of text directing it to the available outputs '''
        sys.stdout.write(text+"\n")
        if self._console_receive_thread:
            if self._console_receive_thread.is_alive():
                self._console_receive_thread.output_text(text) 
               
    
    def execute_command(self,command_line):
        logging.debug('Translating command line %s' % command_line)
        command = self.translator.get_command(command_line)
        if command:
            logging.debug('Executing command %s' % command)
            exec("self."+command)
        else:
            self.output_text('Unknown command: %s' % command_line)
    
    
    def wait_for_console_input(self):
        self._console_receive_thread = mythreading.ReceiveSocketThread(None,self._commands)
        self._console_receive_thread.start()
    

            
        
class MyBotShell(cmd.Cmd):
    prompt = "> "
    bot = None
    
    def do_status(self,line):
        bot.status()
    
    def do_say(self,line):
        bot.say(line)
    
    def do_quit(self,line):
        bot.shutdown()
        return True
    
    def do_list(self,line):
        #TODO: translate list command line
        self.bot.list_modules()
    
    def do_stop(self,line):
        #TODO: translate stop command line
        self.bot.stop_module(line)
                
    def do_start(self,line):
        #TODO: translate start command line
        self.bot.start_module(line)
 
    def do_debug(self,line):
        if not line:
            logging.basicConfig(level=logging.DEBUG)
        





    
logging.basicConfig(level=logging.DEBUG)
logging.debug('Starting...')


bot=MyBot()
bot.wait_for_console_input()

# launching a basic shell
shell=MyBotShell()
shell.bot = bot

shell.cmdloop(" ")


