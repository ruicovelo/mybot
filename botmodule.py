import os
import re
import imp
from glob import glob
from multiprocessing import Process
from ConfigParser import ConfigParser   

# Exchanging objects between processes
from multiprocessing import Queue
from Queue import Empty

# Sharing state between processes
from multiprocessing import Value

from threading import Thread

# Controlling process execution
import signal
import sys

import logging

from commandtranslate import BotCommand,UnknownCommandException

class BotModuleCode(object):

    def __init__(self,code,file_path):
        self.code = code
        self.name = code.__name__
        self._instances = {}
        self.file_path = file_path
    
    def add_instance(self,instance):
        assert not self._instances.has_key(instance.name), 'Instance with name %s already exists!' % instance.name
        self._instances[instance.name]=instance
        
    def remove_instance(self,instance_name):
        assert self._instances.has_key(instance_name), 'Instance with name %s does not exist!' % instance_name
        del self._instances[instance_name]
    
    def get_instances(self):
        return self._instances

class BotModule(object):
    '''
    This should be inherited
    TODO: force this?
    
    This should be used for creating modules, abstracting the part of managing the process that runs the module.
    Multitasking within the module should be done with threads.
    '''
    def __init__(self,name,parameters):
        self._process = None
        self._last_pid = None
        self.log = logging.getLogger(name)
        self.name = name
        self.parameters=parameters
        if self._string_to_bool(self.parameters['Run']):
            self._run = Value('b',True,lock=False)
        else:
            self._run = Value('b',False,lock=False)
        self._commands_queue = Queue()      # queue for receiving asynchronous commands from controller    
        self._output_text_queue = Queue()   # queue for receiving text from controller
        self._receive_output_text = False        # set to True to subscribe to receive text output to stdout 
        
        # default commands
        self._commands={}
        self._commands['start']='self.start()'
        #self._commands['stop']='self.stop()' # for now, stop should only be started by the controller by explicitly calling stop
        
    def _init_process(self):
        self._process = Process()
        self._process.run = self.run
    
    def get_commands(self):
        return self._commands.keys()
    
    def add_command(self,name,command,arguments):
        command = BotCommand(self.name,name,command)
        for argument in arguments:
            command.add_argument(argument[0], argument[1])
        self._commands[name]=command
    
    def validate_command(self,command):
        try:
            available_command = self._commands[command.name]
            if available_command.validate(command.arguments):
                return command
        except KeyError:
            raise UnknownCommandException
    
    def _do_work(self):
        self.log.debug('Not doing the right work...')
        pass
    
    def run(self):     
        signal.signal(signal.SIGTERM,self.stop)   # by default if we get a SIGTERM we will try to stop smoothly

    def status(self,arguments=None):
        if self._run.value == True and self._process and self._process.is_alive():
            return "Running"
        else:
            return "Stopped or stopping"  #TODO: better status support
    def pid(self):
        return self._last_pid
           
    def start(self,arguments=None):
        try:
            #TODO: check if process is running
            self._init_process()
            self._run.value=True
            #TODO: change Thread to MyThread (stoppable thread)
            self._work_thread = Thread(target=self._do_work)
            self._process.start()
            self.log.debug('Starting with pid %d... ' % self._process.pid)
            self._last_pid = self._process.pid
            return True
        except:
            return False
        
    def _forced_stop(self,signum,frame):
        self.log.debug('Stopping NOW %s ' % self.name)
        sys.exit()  
    
    def force_stop(self): #TODO: untested
        self.log.debug('%d force stopping %d!' % (os.getpid(),self._process.pid))
        self._process.terminate()
        
    def kill(self):
        self.log.debug('%d killing %d!' % (os.getpid(),self._process.pid))
        try:
            os.kill(self._process.pid, signal.SIGKILL)
        except OSError:
            pass
    
    def terminate(self):
        self.log.debug('%d terminating %d!' % (os.getpid(),self._process.pid))
        self._process.terminate()
    
    def join(self,timeout):
        self._process.join(timeout)
    
    def is_alive(self):
        if self._process:
            return self._process.is_alive()
        else:
            return False
        
    # Tell module to stop as soon as possible (module has to check the _run flag)
    # This method should be overridden if the module can stop at any time with a SIGTERM signal
    # In that case call force_stop instead.
    def stop(self,arguments=None):
        self.log.debug('%d stopping %d %s!' % (os.getpid(),self._process.pid,self.name))
        self._run.value=False
               
    def stopping(self):
        return not self._run.value
 
    def running(self):
        return self._run.value

    def queue_command(self,command,timeout=None):
        ''' Add command to the queue of commands to process in order '''
        self.log.debug('Adding command to queue\n %s' % command)
        self._commands_queue.put(obj=command, block=True, timeout=timeout)
        
    def _get_command_available(self):
        command = None
        if not self._commands_queue.empty():
            command = self._commands_queue.get_nowait()
        return command
    
    def _wait_next_command_available(self,timeout=None):
        try:
            command = self._commands_queue.get(True, timeout)
            return command
        except Empty:
            return False
        except IOError, e:
            if e.errno == 4:
                return False
            raise(e)
        
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
            self.output_text('Unknown command: %s' % command)    
   
class BotModules(object):
    '''
    A list of BotModules and methods for loading and managing the availability of the modules.
    '''
    def __init__(self,module_path):
        self.log = logging.getLogger('BotModules')
        self._MODULE_PATH = module_path
        self._loaded_modules={}         # code imported and available for launching instances of the modules (not runnable)
        self._instances={}              # dictionary of available instances of modules (runnable) key=instance name, item=BotModule
        self._running_instances = {}                 # workaround to keep child processes accounted for
        self.load_modules()

    def _add_module(self,loaded_module):
        if self._loaded_modules.has_key(loaded_module.name):
            raise Exception('Reloading of existing modules is not yet implemented')
        else:
            self._loaded_modules[loaded_module.name]=loaded_module

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
        
    def add_running_instance(self,instance):
        self._running_instances[instance.pid()]=instance
        
    def remove_running_instance(self,pid):
        del self._running_instances[pid]
        
    def get_running_instance(self,pid):
        return self._running_instances[pid]
    
    def get_running_instances(self):
        return self._running_instances

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
            loaded_module_code = imp.load_source(module_name,file_path)
            loaded_module = BotModuleCode(loaded_module_code,file_path)
            self._add_module(loaded_module)
            return loaded_module
        except Exception as e:
            self.log.error('Unable to load module!')
            self.log.error(str(type(e)) + '\n'+ str(e))
            return False

    def initialize_module(self,loaded_module):
        '''
        Loads configuration parameters from loaded_module configuration file, applies to loaded_module and prepares instances for running.
        '''
        config_parser = ConfigParser()
        config_file_path = os.path.join(self._MODULE_PATH+loaded_module.name+'.cfg')
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
            
            new_instance_name = None
            if configuration_values.has_key('name'):
                new_instance_name = configuration_values['name']
            else:
                new_instance_name = loaded_module.name
            n = 1
            while self._instances.has_key(new_instance_name):
                new_instance_name = loaded_module.name + str(n)
                n = n + 1
            
            self.create_instance(loaded_module=loaded_module, instance_name=new_instance_name, parameters=configuration_values)

    def create_instance(self,loaded_module,instance_name,parameters):
        new_instance = None
        logger = logging.getLogger(instance_name)
        logger.add_log_file(instance_name+'.log')
        logger.add_log_file('common.log')
        logger.setLevel(logging.DEBUG)
        exec('new_instance = loaded_module.code.%s(name=instance_name,parameters=parameters)' % (loaded_module.name))
        self._instances[instance_name]=new_instance
        loaded_module.add_instance(new_instance)
        
    def remove_instance(self,loaded_module,instance_name):
        assert self._instances.has_key(instance_name), 'Instance with name %s does not exist!' % instance_name
        del self._instances[instance_name]
        loaded_module.remove_instance(instance_name)