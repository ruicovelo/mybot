from botmodule import BotModule
from Queue import Empty
from os import unlink
import socket
from mythreading import ReceiveSocketThread
from mythreading import ReceiveQueueThread
import sys

class ConsoleModule(BotModule):
    
    _default_args = {'in_socket_path':'in_console_socket','out_socket_path':'out_console_socket'}
    _receive_client_thread = None
    _receive_controller_thread = None
    in_socket = None
    out_socket = None

    def __init__(self,name='console',parameters={},log=None):
        super(ConsoleModule,self).__init__(name=name,parameters=parameters,log=log)
        self._receive_output_text = True        # setup to receive output_text from controller to send to client
        for arg in self._default_args:
            if not self.parameters.has_key(arg):
                self.parameters[arg] = self._default_args[arg]    
 
    def stop(self):
        super(ConsoleModule,self).stop()
        # stopping gently
        if self._receive_client_thread and self._receive_client_thread.is_alive():
            self._receive_client_thread.stop()
        if self._receive_controller_thread and self._receive_controller_thread.is_alive():
            self._receive_controller_thread.stop()
        if self._receive_client_thread:
            self._receive_client_thread.join(self._receive_client_thread.STOP_TIMEOUT_SECS)
            if self._receive_client_thread.is_alive():
                self.log.error('_receive_client_thread taking too long to close!')
        if self._receive_controller_thread:
            self._receive_controller_thread.join(self._receive_controller_thread.STOP_TIMEOUT_SECS)
            if self._receive_controller_thread:
                self.log.error('_receive_controller_thread taking too long to close!')
        # stopping not so gently
        self.terminate()
    
    def _forced_stop(self,signum,frame):
        #TODO: send client goodbye?
        if self.in_socket:
            self.in_socket.close()
        if self.out_socket:
            self.out_socket.close()
        sys.exit()
    
    def _process_client_data(self,data):
        self.output_command(data)               # send command line received from client to controller

    def _process_controller_data(self,data):
        self.out_socket.sendall(data)           # send to client data sent by controller
        
    def run(self):
        self.in_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            unlink(self.parameters['in_socket_path'])
        except:
            pass
        self.log.debug('Creating socket %s ' % self.parameters['in_socket_path'])
        self.in_socket.bind(self.parameters['in_socket_path'])
        self.in_socket.listen(0)
        self.log.debug('Waiting for connection...')
        self._conn,addr=self.in_socket.accept()
        if not self._conn or self.stopping():
            self.log.debug('Terminating')
            self.log.debug(str(self.stopping()))
            return
        self.log.debug('Connection accepted.')
        self.log.debug('Connecting back to client...')
        self.out_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            self.out_socket.connect(self.parameters['out_socket_path'])
        except:
            self.log.error('Could not connect back to client')
            #TODO: terminate main connection and return to listening for new connections
            self.out_socket = None
        
        
        self._receive_client_thread = ReceiveSocketThread(processing_function=self._process_client_data,connection=self._conn)
        self._receive_client_thread.name='receive_client_thread'
        self._receive_controller_thread = ReceiveQueueThread(processing_function=self._process_controller_data,queue=self._output_text_queue)
        self._receive_client_thread.start()
        self._receive_controller_thread.start()
        
        while not self.stopping():
            try:
                s = self._commands_queue.get(block=True, timeout=5)
                self.log.debug(s)
            except Empty:
                continue
            if not self.stopping():
                self.out_socket.sendall(s)   

        self.out_socket = None
        self.in_socket.close()
        try:
            unlink(self.parameters['in_socket_path'])
        except:
            pass
        
