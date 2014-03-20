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
from commandtranslate import BotCommandTranslator,BotCommand
from botmodule import BotModules

class MyBot(object):
    
    name = "MyBot"
    _MODULE_PATH='modules/'
    _THREAD_TIMEOUT_SECS = 5.0
    
    def __init__(self):
        signal.signal(signal.SIGTERM,self._stop_signal_handling)
        signal.signal(signal.SIGQUIT,self._stop_signal_handling)
        signal.signal(signal.SIGINT,self._stop_signal_handling)
        signal.signal(signal.SIGCHLD,self._child_death)
     
        
        self._outputs_subscribers = []      # instances that want to receive output text from controller
        self._outputs_queue = Queue()       # queue for text to be output by instances to controller
        self._commands_queue = Queue()      # queue for commands to be output by instances to controller
        self._config()
        
        # Starting the thread that will receive text to process (display/save/send)
        self._receive_outputs_thread = mythreading.ReceiveQueueThread(self.output_text,self._outputs_queue)
        self._receive_outputs_thread.start()
        
        # Loading modules and starting instances configured for auto start
        self._modules = BotModules(self._MODULE_PATH)        

        self.translator = BotCommandTranslator(self._modules)

    #botcommand = BotCommand(destination=None,name='send',command='send',arguments=None,origin=None)
    #botcommand.add_argument('to', '.+@.+')
    #botcommand.add_argument('subject','.+')
    #botcommand.add_argument('body','.*')
    #arguments = ['rui.covelo@gmail.com', 'subject', 'test', 'body', 'saldkl kasdlk ldalk']
    #botcommand.validate(arguments)        
        
        #TODO: add more controller commands
        self._commands = {}
        self.add_command(BotCommand(destination=None,name='shutdown',command='self.shutdown()'))
        self.add_command(BotCommand(destination=None,name='list',command='self.list_modules()'))
        command = BotCommand(destination=None,name='start',command='self.start(arguments)')
        command.add_argument('module', '.+')
        self.add_command(command)
        command = BotCommand(destination=None,name='stop',command='self.stop(arguments)')
        command.add_argument('module', '.+')
        self.add_command(command)

        #self._commands['shutdown']='self.shutdown()'
        #self._commands['list']='self.list_modules()'
        #self._commands['start']='self.start(arguments)'
        #self._commands['stop']='self.stop(arguments)'
        #self._commands['reload']='self.reload(arguments)'
        #self.translator.add_commands(None,self._commands)
        

    
    def add_command(self,command):
        self._commands[command.name]=command

    def _config(self):
        config_parser = ConfigParser()
        config_file_path = 'MyBot.cfg' #TODO: set this elsewhere
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
        
    def _child_death(self,signum,frame):
        (pid,exit_code) = os.wait()
        try:
            instance = self._modules.get_running_instance(pid)
            self._modules.remove_running_instance(pid)
        except ValueError:
            self.log.error('Not a running instance?')
            return
        if exit_code != 0:
            self.log.error('%s crashed with exit code %d' % (instance.name,exit_code))
            #TODO: actions? restart? notify?
        else:
            self.log.debug('%s stopped.' % (instance.name))

    def _stop_signal_handling(self,signum,frame):
        self.shutdown()

    # COMMANDS
    def reload(self,arguments=None):
        if arguments:
            module_name=arguments[0]
            module = self._modules.get_modules()[module_name]
            instances = module.get_instances().values()
            for instance in instances:
                self.stop({'module':instance.name})
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
            instance_name = arguments['module']
            instance = self._modules.get_instance(instance_name)
            if instance:
                self.output_text('Starting %s ' % instance.name)
                self.translator.add_commands(destination_name=instance_name, commands=instance.get_commands()) #TODO: add specific commands
                instance.set_output_queue(self._outputs_queue)
                instance.check_outputs_subscriber(self._outputs_subscribers)
                instance.set_output_commands_queue(self._commands_queue)
                if instance.start():
                    self._modules.add_running_instance(instance)
            else:
                self.output_text('Instance not known: %s' % instance_name)                              
                
    def stop(self,arguments=None):
        if arguments:
            instance = self._modules.get_instance(arguments['module'])
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
        running_instances = self._modules.get_running_instances()
        text = ''
        for module in modules:
            text = text + "\nInstances of %s: \n" % module.name
            instances = module.get_instances()
            if not instances:
                text = text + '** No instances available! \n'
                continue
            for instance in instances.values():
                if running_instances.has_key(instance.pid()):
                    status = 'Running with PID %d' % instance.pid()
                else:
                    status = 'Stopped'
                text = text + "\t%s\t\t%s\n" % (instance.name,status)
        self.output_text("%s\n" % text)
 
    # EO COMMANDS /
    
                
    def output_text(self,text):
        ''' Handle the output of text directing it to the available outputs '''
        sys.stdout.write(str(text)+"\n")
        for o in self._outputs_subscribers:
            if o: #TODO: review this 'if'
                o.put(str(text)+"\n")
    
    def execute_command(self,command_line):
        self.log.debug('Translating command line %s' % command_line)
        command = self.translator.validate(command_line)
        if command==True:
            self.log.debug('Now talking to %s ' % self.translator.get_current_destination())
            return
        if command:
            if not command.destination:
                # command sent to controller
                #TODO: remove this when controller has been migrated to a module
                try:
                    available_command = self._commands[command.name]
                    arguments = available_command.validate(command.arguments)
                    self.log.debug('Executing command %s' % available_command)
                    self.log.debug(arguments)
                    exec(available_command.command)
                    return
                except KeyError:
                    self.output_text('KeyError: Unknown command: %s\n' % command_line)
                    return
                except Exception,e:
                    self.output_text(str(e))
                    return
            self.log.debug('Send command to %s ' % command.destination)
            self._modules.get_instance(command.destination).add_command(command)
        else:
            self.output_text('Unknown command: %s\n' % command_line)
       
    def run(self):
        self._shuttingdown = False
        instances = self._modules.get_instances()
        for instance_name in instances:
            if instances[instance_name].running():
                self.start({'module':instance_name})
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
try:
    bot.run()
except Exception,e:
    print(str(e))
    bot.shutdown()
    raise
print('Main thread exiting...')


