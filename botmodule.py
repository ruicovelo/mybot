import os
import re
import imp
from time import sleep
from glob import glob
from multiprocessing import Process
from ConfigParser import ConfigParser   

# Exchanging objects between processes
from multiprocessing import Queue

# Synchronization between processes
from multiprocessing import Lock 

# Sharing state between processes
from multiprocessing import Value
from multiprocessing import Array

from threading import Thread

# Controlling process execution
import signal
import sys

import logging

from commandtranslate import BotCommandTranslator

class BotModule(object):
    '''
    This should be inherited
    TODO: force this?
    
    This should be used for creating modules, abstracting the part of managing the process that runs the module.
    Multitasking within the module should be done with threads.
    '''
    _process = None
    
    parameters = None               # configured startup parameters
    name = None
    
    _run = None                     # set to False to stop module as soon as it checks this value (self._stopping())
    _commands_queue = None          # queue for receiving asynchronous commands from controller    
    _commands_output_queue = None   # queue for sending commands to controller
    _output_text_queue = Queue()    # queue for receiving text from controller
    _output_queue = None            # queue to output data to controller
    _receive_output_text = False    # set to True to subscribe to receive text output to stdout
    _commands = {}
    
    # for background working while main thread receives commands i.e.
    _work_thread = None
    def __init__(self,name,parameters):
        signal.signal(signal.SIGTERM,self._forced_stop)
        self.log = logging.getLogger(name)
        self.name = name
        self.parameters=parameters
        if self.parameters['Run']=='True': #TODO: check other possible values for True (case, yes, 1, ...)
            self._run = Value('b',True,lock=False)
        else:
            self._run = Value('b',False,lock=False)
        self._commands_queue = Queue()    
        self.log.debug('Module named "%s" initiating...' % self.name)
        
        # default commands
        self._commands['start']='self.start()'
        #self._commands['stop']='self.stop()' # for now, stop should only be started by the controller by explicitly calling stop
        
    def _init_process(self):
        self._process = Process()
        self._process.run = self.run
    
    def get_commands(self):
        return self._commands.keys()
    
    def _do_work(self):
        self.log.debug('Not doing the right work...')
        pass
    
    def run(self):
        self.log.debug('This function should be overriden')
        pass

    def status(self,arguments=None):
        if self._run.value == True and self._process.is_alive():
            return "Running"
        else:
            return "Stopped or stopping"  #TODO: better status support
           
    def start(self,arguments=None):
        #TODO: check if process is running
        self._init_process()
        self._run.value=True
        #TODO: change Thread to MyThread (stoppable thread)
        self._work_thread = Thread(target=self._do_work)
        #super(BotModule,self).start()
        self._process.start()
      
    def _forced_stop(self,signum,frame):
        self.log.debug('Stopping NOW %s ' % self.name)
        sys.exit()  
    
    def force_stop(self):
        self._process.terminate()
    
    def terminate(self):
        self._process.terminate()
        
    # Tell module to stop as soon as possible (module has to check the _run flag)
    # This method should be overriden if the module can stop at any time with a SIGTERM signal
    # In that case call force_stop instead.
    def stop(self,arguments=None):
        self.log.debug('Stopping %s ...' % self.name)
        self._run.value=False
               
    def stopping(self):
        return not self._run.value
 
    def running(self):
        return self._run.value

    def add_command(self,command,timeout=None):
        ''' Add command to the queue of commands to process in order '''
        self.log.debug('Adding command to queue\n %s' % command.tostring())
        self._commands_queue.put(obj=command, block=True, timeout=timeout)
 
    def _get_command_available(self):
        command = None
        if not self._commands_queue.empty():
            command = self._commands_queue.get_nowait()
        return command
    
    def _wait_next_command_available(self,timeout=None):
        return self._commands_queue.get(True, timeout)
        
    def set_output_queue(self,q):
        self._output_queue = q
        
    def check_outputs_subscriber(self,l):
        if self._receive_output_text:
            l.append(self._output_text_queue)

    def set_commands_queue(self,q):
        self._commands_queue = q

    def set_output_commands_queue(self,q):
        self._output_commands_queue = q
        
    def output_command(self,command_line):
        if self._output_commands_queue:
            self._output_commands_queue.put(command_line)
            return True
        return False
    
    def output(self,arguments):
        if self._output_queue:
            self._output_queue.put(arguments)
            return True
        return False

    def _string_to_bool(self,s):
        try:
            if s.lower() in ['true','yes','1']:
                return True
            else:
                return False
        except AttributeError:
            return s
        
    def _execute(self,command):
        if command and command.destination==self.name:
            self.log.debug('Executing command %s' % command)
            command.command(command.arguments)
        else:
            self.output_text('Unknown command: %s' % command.tostring())    
   

class BotModules(object):
    '''
    A list of BotModules and methods for loading and managing the availability of the modules.
    '''
    
    _MODULE_PATH = None
    _loaded_modules=[]          # code imported and available for launching instances of the modules
    _instances={}               # dictionary of available instances of modules (running modules) key=instance name, item=BotModule

    def __init__(self,module_path):
        self.log = logging.getLogger('BotModules')
        self._MODULE_PATH = module_path
        self.load_modules()

    def _get_available_modules_files(self):
        '''
        Search the modules path for files available to import as modules
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

    def get_modules(self):
        return self._loaded_modules
    
    def get_instances(self):
        return self._instances
    
    def get_instance(self,instance_name):
        try:
            return self._instances[instance_name]
        except KeyError:
            return None        

    def load_modules(self):
        '''
        Import modules class definitions and code. Does not expect to run any code in the module.
        The modules are appended to self._loaded_modules
        '''
        available_modules_files = self._get_available_modules_files()
        for file_path in available_modules_files:
            loaded_module = self.load_module(file_path)
            if loaded_module:
                self.initialize_module(loaded_module)

    def load_module(self,file_path):
        '''
        Load the code for the module. Should not run any instance of the module!
        '''
        #TODO: make sure we are not running any code in the module (code not inside classes)
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        self.log.info("Importing module '%s' from %s" % (module_name,file_path))
        try:
            loaded_module = imp.load_source(module_name,file_path)
            self._loaded_modules.append(loaded_module)
            return loaded_module
        except Exception as e:
            self.log.error('Unable to load module!')
            self.log.error(str(type(e)) + e.message)
            return False

    def initialize_module(self,loaded_module):
        '''
        Loads configuration parameters from loaded_module configuration file, applies to loaded_module and prepares instances for running.
        '''
        config_parser = ConfigParser()
        config_file_path = os.path.join(self._MODULE_PATH+loaded_module.__name__+'.cfg')
        initialization_values = {}

        # by default, we will only run one instance of each module
        self._configuration_defaults={'Instances': 1,'Run': False}
        
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
            
            new_instance = None
            new_instance_name = None
            if configuration_values.has_key('name'):
                new_instance_name = configuration_values['name']
            else:
                new_instance_name = loaded_module.__name__
            n = 1
            while self._instances.has_key(new_instance_name):
                new_instance_name = loaded_module.__name__ + str(n)
                n = n + 1
             
            logger = logging.getLogger(new_instance_name)
            logger.add_log_file(new_instance_name+'.log')
            logger.add_log_file('common.log')
            logger.setLevel(logging.DEBUG)
            exec('new_instance = loaded_module.%s(name=new_instance_name,parameters=configuration_values)' % (loaded_module.__name__))
            self._instances[new_instance.name]=new_instance


