from botmodule import BotModule
from multiprocessing import Queue
from Queue import Empty
from os import unlink
import socket
from mythreading import ReceiveSocketThread
from mythreading import ReceiveQueueThread


class ConsoleModule(BotModule):
    
    _default_args = {'in_socket_path':'in_console_socket','out_socket_path':'out_console_socket'}

    def __init__(self,name='console',parameters={},log=None):
        super(ConsoleModule,self).__init__(name=name,parameters=parameters,log=log)
        self._receive_output_text = True        # setup to receive output_text from controller to send to client
        for arg in self._default_args:
            if not self.parameters.has_key(arg):
                self.parameters[arg] = self._default_args[arg]    
 
    def stop(self):
        super(ConsoleModule,self).stop()
        self.terminate()
    
    def _process_client_data(self,data):
        self.output_command(data)

    def _process_controller_data(self,data):
        self.log.debug('Processing controller data')
        self.out_socket.sendall(data)
        
    def run(self):
        self.in_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            unlink(self.parameters['in_socket_path'])
        except:
            pass

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
        
        
if __name__ == '__main__':
    b = ConsoleModule()