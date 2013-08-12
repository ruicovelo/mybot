'''
Created on Jul 26, 2013

@author: pedro
'''
from pickle import NONE

print "Initializing bot..."

from communication import voice
from communication import myemail


from glob import glob
import re
from os import path
import logging
import cmd
import imp
from multiprocessing import Queue

from ConfigParser import ConfigParser
from threading import Thread


class MyBot(object):
    '''
    classdocs
    '''
    name = "MyBot"
    _voice = voice.Voice()
    
    _MODULE_PATH='modules/'
    _loaded_modules=[]
    _runnable_modules={}
    _outputs = Queue()
    

    
    
    def get_available_modules_files(self):
        modules_list = []
        all_files = glob(self._MODULE_PATH+"/*.py")
        logging.debug(all_files)
        module_name_reg=re.compile('[A-Z][a-z0-9]*Module.py')
        for file_path in all_files:
            filename = path.basename(file_path)
            if module_name_reg.match(filename):
                modules_list.append(file_path)
        return modules_list
        
        
    
    
    
    def load_modules(self):
        logging.debug('load_modules')
        available_modules_files = self.get_available_modules_files()
        for file_path in available_modules_files:
            module_name = path.splitext(path.basename(file_path))[0]
            logging.info("Importing module '%s' from %s" % (module_name,file_path))
            try:
                loaded_module = imp.load_source(module_name,file_path)
                self._loaded_modules.append(loaded_module)
            except Exception as e:
                logging.error('Unable to load module!')
                logging.error(str(type(e)) + e.message)




    def launch_module(self,loaded_module):
        config_parser = ConfigParser()
        config_file_path = path.join(self._MODULE_PATH+loaded_module.__name__+'.cfg')
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
        
        last_name = None
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
            new_module.start()
            
        
    
    


    def say(self,text):
        #TODO: move this to a module
        if not self._voice.speak(text):
            print "Don't have voice?!"
  

    def __init__(self):
        '''
        Constructor
        '''
#         self.say("Waking up...")
#         if self.name:
#             self.say("My name is " + self.name)
#         else:
#             self.say("Hmm... Don't know my name... Should you give me a name? That would be cool...")
        logging.debug('Initializing MyBot')
        self.load_modules()
        for loaded_module in self._loaded_modules:
            self.launch_module(loaded_module)
            
        
    def status(self):
        print "Name: ", self.name


    def _receive_output(self):
        logging.debug('Receive thread starting...')
        while True:
            s = self._outputs.get(block=True, timeout=30)
            print s
            

    def wait_for_output(self):
        self._receive_thread = Thread(target=self._receive_output)
        self._receive_thread.start()
        
    def get_runnable_modules(self):
        runnable_modules = []
        for runnable_module in self._runnable_modules.keys():
            runnable_modules.append((runnable_module,self._runnable_modules[runnable_module].is_alive()))
        return runnable_modules

    def stop_module(self,module_name):
        print self._runnable_modules.keys()
        loaded_module = self._runnable_modules[module_name]
        loaded_module.stop()

        
class MyBotShell(cmd.Cmd):
    prompt = "> "
    bot = None
    
    def do_status(self,line):
        bot.status()
    
    def do_say(self,line):
        bot.say(line)
    
    def do_quit(self,line):
        return True
    
    def do_list(self,line):
        runnable_modules = self.bot.get_runnable_modules()
        print ""
        for rm in runnable_modules:
            print rm
    
    def do_stop(self,line):
        line = line.lower()
        runnable_modules=self.bot.get_runnable_modules()
        for rm in runnable_modules:
            if line in rm[0].lower() and rm[1]:
                self.bot.stop_module(rm[0])
                
    def do_start(self,line):
        line = line.lower()
        runnable_modules=self.bot.get_runnable_modules()
        for rm in runnable_modules:
            if line in rm[0].lower() and rm[1]:
                self.bot.start_module(rm[0])               

    def do_debug(self,line):
        if not line:
            logging.basicConfig(level=logging.DEBUG)
        

    
logging.basicConfig(level=logging.DEBUG)
logging.debug('Starting...')
bot=MyBot()
bot.wait_for_output()


shell=MyBotShell()
shell.bot = bot
bot.say("Waiting for your commands.")

shell.cmdloop(" ")

    