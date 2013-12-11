import sys
import os
import signal
import logging
from ConfigParser import ConfigParser   
from multiprocessing import Queue
from Queue import Empty
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
    _outputs_subscribers = []
    _outputs_queue = Queue()
    _commands_queue = Queue()
    _commands = {}

    translator = None
    
    _shuttingdown = False
    
    _THREAD_TIMEOUT_SECS = 5.0
    _receive_outputs_thread = None      # waits for outputs from running modules
    
    def __init__(self):
        signal.signal(signal.SIGTERM,self._SIGTERM)
        signal.signal(signal.SIGQUIT,self._SIGQUIT)
        signal.signal(signal.SIGINT,self._SIGINT)
        signal.signal(signal.SIGCHLD,self.child_death)
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
        self.log.debug('Initializing MyBot with PID %d...' % os.getpid())
        
        # Starting the thread that will receive text to process (display/save/send)
        self._receive_outputs_thread = mythreading.ReceiveQueueThread(self.output_text,self._outputs_queue)
        self._receive_outputs_thread.start()

        self.translator = BotCommandTranslator()
        #TODO: add more controller commands
        self._commands['quit']='self.shutdown()'
        self._commands['shutdown']='self.shutdown()'
        self._commands['list']='self.list_modules()'
        self._commands['start']='self.start(arguments)'
        self._commands['stop']='self.stop(arguments)'
        self.translator.add_commands(None,self._commands)
        
        # Loading modules and starting instances configured for auto start
        self._modules = BotModules(self._MODULE_PATH)

    def _SIGTERM(self,signum,frame):
        self.shutdown()

    def _SIGQUIT(self,signum,frame):
        self.shutdown()
        
    def _SIGINT(self,signum,frame):
        self.shutdown()

    def child_death(self,signum,frame):
        (pid,exit_code) = os.wait()
        instances = self._modules.get_instances().values()
        for instance in instances:
            if instance.pid() == pid:
                if exit_code != 0:
                    self.log.error('%s crashed with exit code %d' % (instance.name,exit_code))
                    #TODO: actions? restart? notify?
                return 

    # COMMANDS
    def start(self,arguments=None):
        if arguments:
            instance_name = arguments[0]
            instance = self._modules.get_instance(instance_name)
            if instance:
                self.output_text('Starting %s ' % instance.name)
                self.translator.add_commands(destination_name=instance_name, commands=instance.get_commands()) #TODO: add specific commands
                instance.set_output_queue(self._outputs_queue)
                instance.check_outputs_subscriber(self._outputs_subscribers)
                instance.set_output_commands_queue(self._commands_queue)
                instance.start()
            else:
                self.log.error('Instance not known: %s' % instance_name)                              
                
    def stop(self,arguments=None):
        if arguments:
            instance = self._modules.get_instance(arguments[0])
            if instance:
                if instance.running():
                    self.output_text('Stopping %s ' % instance.name)
                    instance.stop()
                    #TODO: check if instance really stopped
                    
    def shutdown(self,arguments=None):
        if self._shuttingdown:
            return
        self._shuttingdown = True
        self.output_text('Controller shutting down...')
        
        # Shutting down instances of modules
        instances = self._modules.get_instances()
        for instance_name in instances:
            instance = self._modules.get_instance(instance_name)
            if instance.running():
                instance.stop()
                
        for instance_name in instances:
            instance = self._modules.get_instance(instance_name)
            if instance.is_alive():
                self.log.info('Waiting for %s to stop...' % instance_name)
                instance.join(self._THREAD_TIMEOUT_SECS)
                if instance.is_alive():
                    self.log.info('%s taking too long to stop. Terminating...' % instance_name)
                    instance.terminate()
                    instance.join(self._THREAD_TIMEOUT_SECS)
                    self.log.error('%s still not dead!' % instance_name)
        
        if self._receive_outputs_thread:
            self._receive_outputs_thread.stop()
 
        self._receive_outputs_thread.join(self._THREAD_TIMEOUT_SECS)
 
        #TODO: not sure if this is necessary
        if self._receive_outputs_thread.is_alive():
            self.log.error('Receive outputs thread is taking too long to close...')
        self.log.debug('Outputs thread closed.')   
        logging.shutdown()
        

    def _get_module(self,module_name):
        if self._modules.get_instances().has_key(module_name):
            return self._modules.get_instances()[module_name]
        return False

    def list_modules(self,arguments=None):
        instances = self._modules.get_instances()
        if not instances:
            self.output_text('No instances available!')
            return

        self.output_text('Available instances of modules:')
        for instance in instances:
            self.output_text("%s\t\t%s" % (instance,instances[instance].status()))
    
    def say(self,arguments):
        #TODO: move this to a module
        if not self._voice.speak(arguments):
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
        command = self.translator.validate(command_line)
        if command==True:
            self.log.debug('Now talking to %s ' % self.translator.get_current_destination())
            return
        if command:
            if not command.destination:
                self.log.debug('Executing command %s' % command.tostring())
                arguments = command.arguments
                exec(self._commands[command.name])
                return
            self.log.debug('Send command to %s ' % command.destination)
            self._modules.get_instance(command.destination).add_command(command)
        else:
            self.output_text('Unknown command: %s' % command_line)
       
    def run(self):
        instances = self._modules.get_instances()
        for instance_name in instances:
            if instances[instance_name].running():
                self.start([instance_name])        
        while not self._shuttingdown:
            try:
                s = self._commands_queue.get(block=True, timeout=3)
            except Empty:
                # Timeout 
                continue
            except IOError, e:
                if e.errno == 4:
                    # This will happen if we receive a signal out of Queue.get
                    continue
                print(str(e))
                continue
            self.execute_command(s)


logging.setLoggerClass(MyLogger)
bot=MyBot()
bot.run()
print('Main thread exiting...')


