import sys
import logging
import cmd  #TODO: lose this
from ConfigParser import ConfigParser   
from multiprocessing import Queue
import mythreading
from mylogging import MyLogger

# My modules
from communication import voice
from commandtranslate import BotCommandTranslator
from botmodule import BotModules

class MyBot(object):
    name = "MyBot"
    _voice = voice.Voice()
    
    _MODULE_PATH='modules/'
    _modules = None
    _outputs = Queue()
    _commands = Queue()
    _outputs_subscribers = []

    
    translator = None
    
    _shuttingdown = False
    
    _THREAD_TIMEOUT_SECS = 5.0
    _receive_commands_thread = None     # waits for commands from running modules
    _receive_outputs_thread = None      # waits for outputs from running modules
    
    def __init__(self):
        config_parser = ConfigParser()
        config_file_path = 'MyBot.cfg'
        config_parser.read(config_file_path)
        configuration_values={'LogLevel': logging.DEBUG}         # set default values here
        if not config_parser.has_section('Initialization'):
            config_parser.add_section('Initialization')
            
        for default in configuration_values:
            if config_parser.has_option('Initialization', default):
                configuration_values[default] = config_parser.get('Initialization', default)
            else:
                config_parser.set('Initialization', default, configuration_values[default])
        
        config_parser.write(open(config_file_path,"w"))


        self.log = logging.getLogger(self.name)
        self.log.setLevel(int(configuration_values['LogLevel']))
        self.log.add_log_file('common.log')
        self.log.debug('Initializing MyBot...')
        
        
        # Starting the thread that will receive commands in the background set from modules
        self._receive_commands_thread = mythreading.ReceiveQueueThread(self.execute_command,self._commands)
        self._receive_commands_thread.start()
        
        # Starting the thread that will receive text to process (display/save/send)
        self._receive_outputs_thread = mythreading.ReceiveQueueThread(self.output_text,self._outputs)
        self._receive_outputs_thread.start()
        
        # Loading modules and starting instances configured for auto start
        self._modules = BotModules(self._MODULE_PATH)
        instances = self._modules.get_instances()
        for instance_name in instances: 
            instances[instance_name].set_output_queue(self._outputs)
            instances[instance_name].check_outputs_subscriber(self._outputs_subscribers)
            instances[instance_name].set_output_commands_queue(self._commands)
            if instances[instance_name].running():
                instances[instance_name].start()
            
        #self.translator = BotCommandTranslator(modules,module_specific_commands)

    # COMMANDS
    
    def shutdown(self):
        self._shuttingdown = True
        self.output_text('Shutting down...')
        
        # Shutting down instances of modules
        instances = self._modules.get_instances()
        for instance_name in instances:
            if instances[instance_name].running():
                instances[instance_name].stop()
        #TODO: join
        
        self._receive_commands_thread.stop()
 
        if self._receive_outputs_thread:
            self._receive_outputs_thread.stop()
 
        self._receive_outputs_thread.join(self._THREAD_TIMEOUT_SECS)
        self._receive_commands_thread.join(self._THREAD_TIMEOUT_SECS)   
 
        #TODO: not sure if this is necessary
        if self._receive_outputs_thread.is_alive():
            self.log.error('Receive outputs thread is taking too long to close...')
        self.log.debug('Outputs thread closed.')
   
        if self._receive_commands_thread.is_alive():
            self.log.error('Receive commands thread is taking too long to close...')
        self.log.debug('Receive commands thread closed.')
        logging.shutdown()
        


    def _get_module(self,module_name):
        if self._modules.get_instances().has_key(module_name):
            return self._modules.get_instances()[module_name]
        return False

    def list_modules(self):
        runnable_modules = self._modules.get_instances()
        if not runnable_modules:
            self.output_text('No modules available!')
            return

        self.output_text('Available modules:')
        for rm in runnable_modules:
            self.output_text("%s\t\t%s" % (rm,runnable_modules[rm].status()))
    
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
 





logging.setLoggerClass(MyLogger)
bot=MyBot()

# launching a basic shell
shell=MyBotShell()
shell.bot = bot

shell.cmdloop(" ")


