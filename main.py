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
    _MODULE_PATH='modules/'
    _THREAD_TIMEOUT_SECS = 5.0
    
    def __init__(self):
        signal.signal(signal.SIGTERM,self._stop_signal_handling)
        signal.signal(signal.SIGQUIT,self._stop_signal_handling)
        signal.signal(signal.SIGINT,self._stop_signal_handling)
        signal.signal(signal.SIGCHLD,self.child_death)
        
        self._outputs_subscribers = []      # instances that want to receive output text from controller
        self._outputs_queue = Queue()       # queue for text to be output by instances to controller
        self._commands_queue = Queue()      # queue for commands to be output by instances to controller

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
        self._commands = {}
        self._commands['shutdown']='self.shutdown()'
        self._commands['list']='self.list_modules()'
        self._commands['start']='self.start(arguments)'
        self._commands['stop']='self.stop(arguments)'
        self._commands['reload']='self.reload(arguments)'
        self.translator.add_commands(None,self._commands)
        
        # Loading modules and starting instances configured for auto start
        self._modules = BotModules(self._MODULE_PATH)

    def _stop_signal_handling(self,signum,frame):
        self.shutdown()

    def child_death(self,signum,frame):
        (pid,exit_code) = os.wait()
        instances = self._modules.get_instances().values()
        for instance in instances:
            if instance.pid() == pid:
                if exit_code != 0:
                    self.log.error('%s crashed with exit code %d' % (instance.name,exit_code))
                    #TODO: actions? restart? notify?
                else:
                    self.log.debug('%s stopped. is_alive() %s' % (instance.name,str(instance.is_alive())))
                return 

    # COMMANDS
    def reload(self,arguments=None):
        if arguments:
            module_name=arguments[0]
            module = self._modules.get_modules()[module_name]
            instances = module.get_instances().values()
            for instance in instances:
                self.stop(instance.name)
                self._modules.remove_instance(module, instance.name)
                #TODO: wait for instances to stop?
            self.list_modules()
            del self._modules.get_modules()[module_name]
            file_path = module.file_path
            module = None
            module = self._modules.load_module(file_path)
            self._modules.initialize_module(module)
            print('Final')
            self.list_modules()
            
                
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
        modules = self._modules.get_modules().values()
        for module in modules:
            self.output_text("Instances of %s: " % module.name)
            instances = module.get_instances()
            if not instances:
                self.output_text('** No instances available!')
                continue
            for instance in instances:
                self.output_text("\t%s\t\t%s" % (instance,instances[instance].status()))
    
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
            if o: #TODO: review this 'if'
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
        self._shuttingdown = False
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


