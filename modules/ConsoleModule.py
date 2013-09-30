

from botmodule import BotModule

from os import unlink
import socket


class ConsoleModule(BotModule):
    
    _default_args = {'in_socket_path':'in_console_socket','out_socket_path':'out_console_socket'}


    def __init__(self,name='console',parameters={},log=None):
        super(ConsoleModule,self).__init__(name=name,parameters=parameters,log=log)
        for arg in self._default_args:
            if not self.parameters.has_key(arg):
                self.parameters[arg] = self._default_args[arg]    
 
    def stop(self):
        self.terminate()
        
    def run(self):
        self.in_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            unlink(self.parameters['in_socket_path'])
        except:
            pass

        self.in_socket.bind(self.parameters['in_socket_path'])
        self.in_socket.listen(0)

        conn,addr=self.in_socket.accept()
        if not conn or self.stopping():
            return
        
        self.out_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            self.out_socket.connect(self.parameters['out_socket_path'])
        except:
            self.out_socket = None
        while not self.stopping():
            data = conn.recv(1024)
            if not data:
                break
            self._queue.put(data)
        conn.close()
        self.out_socket = None
        self.in_socket.close()
        try:
            unlink(self.parameters['in_socket_path'])
        except:
            pass
        
        
if __name__ == '__main__':
    b = ConsoleModule()