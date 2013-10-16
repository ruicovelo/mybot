import os
import re
import sys
import logging
import cmd  #TODO: lose this
import imp                              # loading modules
from glob import glob                   # file system walking
from ConfigParser import ConfigParser   
from multiprocessing import Queue
import mythreading
from mylogging import MyLogger

# My modules
from communication import voice
from commandtranslate import BotCommandTranslator

class MyBot(object):
    name = "MyBot"
    _voice = voice.Voice()
    
    _MODULE_PATH='modules/'
    _loaded_modules=[]		# modules available in modules directory
    _runnable_modules={}	# module objects that can be started
    _outputs = Queue()
    _commands = Queue()
    _outputs_subscribers = []

    
    translator = None
    
    _shuttingdown = False
    
    _THREAD_TIMEOUT_SECS = 5.0
    _receive_commands_thread = None     # waits for commands from running modules
    _receive_outputs_thread = None      # waits for outputs from running modules
    
    def __init__(self):
        self.log = MyLogger(self.name)
        self.log.debug('Initializing MyBot...')
        
        # Loading acceptable commands
        self.translator = BotCommandTranslator()
        self.translator.add_command("list", "list_modules()")
        
        # Starting the thread that will receive commands in the background set from modules
        self._receive_commands_thread = mythreading.ReceiveQueueThread(self.execute_command,self._commands)
        self._receive_commands_thread.start()
        
        # Starting the thread that will receive text to process (display/save/send)
        self._receive_outputs_thread = mythreading.ReceiveQueueThread(self.output_text,self._outputs)
        self._receive_outputs_thread.start()
        
        # Loading modules
        self.load_modules()
        for loaded_module in self._loaded_modules:
            self.launch_module(loaded_module)

    # COMMANDS
    
    def shutdown(self):
        self._shuttingdown = True
        self.output_text('Shutting down...')
        
        # Shutting down modules
        for rm in self.get_runnable_modules():
            self.stop_module(rm[0])
        #TODO: join
        
        self._receive_commands_thread.stop()
 
        if self._receive_outputs_thread:
            self._receive_outputs_thread.stop()
 
        self._receive_outputs_thread.join(self._THREAD_TIMEOUT_SECS)
        self._receive_commands_thread.join(self._THREAD_TIMEOUT_SECS)   
 
        #TODO: not sure if this is necessary
        if self._receive_outputs_thread.is_alive():
            self.log.error('Receive outputs thread is taking too long to close...')
   
        if self._receive_commands_thread.is_alive():
            self.log.error('Receive commands thread is taking too long to close...')
        logging.shutdown()
        
    def get_available_modules_files(self):
        '''
        Search the modules path for files to import as modules
        '''
        modules_list = []
        all_files = glob(self._MODULE_PATH+"/*.py")
        self.log.debug(all_files)
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
        '''
        Import modules class definitions and code. Does not expect to run any code in the module.
        The modules are appended to self._loaded_modules
        '''
        #TODO: make sure we are not running any code in the module (code not inside classes)
        self.log.debug('load_modules')
        available_modules_files = self.get_available_modules_files()
        for file_path in available_modules_files:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            self.log.info("Importing module '%s' from %s" % (module_name,file_path))
            try:
                loaded_module = imp.load_source(module_name,file_path)
                self._loaded_modules.append(loaded_module)
            except Exception as e:
                self.log.error('Unable to load module!')
                self.log.error(str(type(e)) + e.message)

    def launch_module(self,loaded_module):
        '''
        Loads configuration parameters from loaded_module configuration file, applies to loaded_modules and runs it.
        '''
        config_parser = ConfigParser()
        config_file_path = os.path.join(self._MODULE_PATH+loaded_module.__name__+'.cfg')
        initialization_values = {}

        # by default, we will only run one instance of each module
        self._configuration_defaults={'Instances': 1,'Run': True}
        
        self.log.debug("Loading configuration file %s ..." % config_file_path)
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

        # applying configuration values to each instance of the module
        for i in range(1,int(initialization_values['Instances'])+1):
            configuration_values = {}
            
            # searching for specific Instance configuration values
            if config_parser._sections.has_key('Instance ' + str(i)):
                self.log.debug('Loading specific configuration values for %s ...' % 'Instance ' + str(i))
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
                self.log.debug('Loading common configuration values...')
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
             
            logger = MyLogger(new_module_name)
            logger.setLevel(logging.DEBUG)
            exec('new_module = loaded_module.%s(name=new_module_name,parameters=configuration_values)' % (loaded_module.__name__))
            new_module.set_output_queue(self._outputs)
            new_module.check_outputs_subscriber(self._outputs_subscribers)
            new_module.set_output_commands_queue(self._commands)
            self._runnable_modules[new_module.name]=new_module
            if configuration_values['Run'] == 'True':
                new_module.start()

    def _get_module(self,module_name):
        if self._runnable_modules.has_key(module_name):
            return self._runnable_modules[module_name]
        return False

    def start_module(self,module_name):
        loaded_module = self._get_module(module_name)
        if loaded_module:
            loaded_module.start()
            
    def stop_module(self,module_name):
        loaded_module = self._get_module(module_name)
        if loaded_module:
            loaded_module = self._runnable_modules[module_name]
            if loaded_module.is_alive():
                loaded_module.stop()
    
    def say(self,text):
        #TODO: move this to a module
        if not self._voice.speak(text):
            print("Don't have voice?!")
  
    def status(self):
        self.output_text("Name: %s" % self.name)
  
    # EO COMMANDS /
    
                
    def output_text(self,text):
        ''' Handle the output of text directing it to the available outputs '''
        sys.stdout.write(text+"\n")
        for o in self._outputs_subscribers:
            o.put(text+"\n")
    
    def execute_command(self,command_line):
        self.log.debug('Translating command line %s' % command_line)
        command = self.translator.get_command(command_line)
        if command:
            self.log.debug('Executing command %s' % command)
            exec("self."+command)
        else:
            self.output_text('Unknown command: %s' % command_line)
       

            
        
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
 






bot=MyBot()

# launching a basic shell
shell=MyBotShell()
shell.bot = bot

shell.cmdloop(" ")


