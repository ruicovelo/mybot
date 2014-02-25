from botmodule import BotModule
from Queue import Empty
from os import unlink
import socket
from mythreading import ReceiveSocketThread
from mythreading import ReceiveQueueThread
import time
import cPickle
from commandtranslate import BotCommand

class ConsoleThread(ReceiveSocketThread):
    
    def __init__(self,processing_function,log,in_socket_path):
        super(ConsoleThread,self).__init__(processing_function=processing_function,connection=None)
        self.log = log
        self.in_socket_path=in_socket_path
        self.in_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self._connection = None
        try:
            unlink(self.in_socket_path)
        except:
            pass        
        
    def run(self):
        self.in_socket.bind(self.in_socket_path)
        self.in_socket.listen(0)
        
        while not self.stopping():
            self.log.debug('Waiting for connection...')
            self._connection,addr=self.in_socket.accept()
            if not self._connection or self.stopping():
                return
            self.log.debug('Connection accepted.')
            super(ConsoleThread,self).run()
        # If we are here we are stopping or something bad happened
        if self.in_socket:
            self.in_socket.close()
            self.in_socket = None
        try:
            unlink(self.in_socket_path)
        except:
            pass
        
    def send_command(self,arguments):
        self.log.debug('Sending command: %s' % arguments.name)
        self._connection.sendall(cPickle.dumps(arguments))
        
    def stop(self):
        # stopping gently
        if self._connection:
            self.send_command(BotCommand('console','disconnect','disconnect',None,None))
        super(ConsoleThread,self).stop()
        
class ConsoleModule(BotModule):
    
    _default_args = {'in_socket_path':'console_socket'}

    def __init__(self,name='console',parameters={}):
        super(ConsoleModule,self).__init__(name=name,parameters=parameters)
        self._receive_output_text = True        # setup to receive output_text from controller to send to client
        for arg in self._default_args:
            if not self.parameters.has_key(arg):
                self.parameters[arg] = self._default_args[arg]
        self._commands['send']='self.send_command(arguments)'
 
    def _process_client_data(self,data):
        self.log.debug('Client data: %s' % data)
        self.output_command(data)               # send command line received from client to controller

    def _process_controller_data(self,data):
        self.log.debug('Controller data: %s' % data)
        cmd = BotCommand(destination='console',name='output',command=None,arguments=data,origin=None)
        self._console_thread.send_command(cmd)           # send to client data sent by controller
        
    def send_text(self,arguments):
        if self._console_thread.out_socket:
            self._console_thread.out_socket.sendall(str(arguments))
                
    def run(self):
        super(ConsoleModule,self).run()
        self._console_thread = ConsoleThread(processing_function=self._process_client_data,log=self.log,in_socket_path=self.parameters['in_socket_path'])
        
        # To process data received from controller that must be sent to client
        #TODO: not sure if needed / main thread receives commands from controller that might be used to send data to client
        self._receive_controller_thread = ReceiveQueueThread(processing_function=self._process_controller_data,queue=self._output_text_queue)
        self._receive_controller_thread.start()
        #TODO: wait for threads to end?         

        while not self.stopping():
            self._console_thread.start()
            # waiting for commands from controller
            while not self.stopping() and self._console_thread.is_alive():
                try:
                    #TODO: check timeout
                    cmd = self._commands_queue.get(block=True, timeout=3)
                    if cmd:
                        self.log.debug('Received command %s' % cmd.tostring())
                        try:
                            arguments = cmd.arguments
                            exec(self._commands[cmd.name])
                        except KeyError:
                            self.log.debug('Unknown command %s ' % cmd.tostring())
                except Empty:
                    continue
                except IOError,e:
                    if e.errno == 4:
                        continue
            self._console_thread.stop()
            self._receive_controller_thread.stop()
            self._console_thread.join(self._console_thread.STOP_TIMEOUT_SECS)
            self._receive_controller_thread.join(self._receive_controller_thread.STOP_TIMEOUT_SECS)
        
