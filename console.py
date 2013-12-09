import curses
import socket
import os
from mythreading import ReceiveSocketThread
from asyncconsole import AsyncConsole
import cPickle
from commandtranslate import BotCommand
import sys 

IN_CON_SOCKET_PATH = 'in_console_socket'
OUT_CON_SOCKET_PATH = 'out_console_socket'
line_number = 0

class ConsoleReceiveSocketThread(ReceiveSocketThread):
    
    def __init__(self,connection,in_socket,out_socket,console):
        super(ConsoleReceiveSocketThread,self).__init__(processing_function=self.handle_received_output,connection=connection)
        self.in_socket = in_socket
        self.out_socket = out_socket
        self.console = console
        
    def handle_received_output(self,data):
        cmd=cPickle.loads(data)
        if cmd.name == 'output':
            # ugly hack that will be removed when a communication protocol is implemented
            # avoids extra line breaks
            if cmd.arguments[-1:] == '\n':
                cmd.arguments=cmd.arguments[:-1]
            self.addline(cmd.arguments)
            return
        #TODO: remove quit
        if cmd.name == 'quit' or cmd.name == 'disconnect':
            self.disconnect()
            self.addline('Connection closed')
    
    def disconnect(self):
        self.stop()
        in_con_socket.close()
        out_con_socket.close()

    def addline(self,line):
        #TODO: replace globals, use __init__ to pass variables if possible
        global line_number
        line_number = line_number + 1
        #TODO: count \n in line
        self.console.addline(line)

def main(stdscr):
    global console
    console = AsyncConsole(stdscr)
    # This is clumsy and will sometimes fail; server might be faster to connect back 
    # before we have a socket ready
    # This will be fixed when we implement a communication protocol
    global in_con_socket
    global out_con_socket
    in_con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    in_con_socket.connect(IN_CON_SOCKET_PATH)
    out_con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    out_con_socket.bind(OUT_CON_SOCKET_PATH)
    out_con_socket.listen(1)
    console.addline('Connected to server. Waiting for server to connect back to client...')
    conn,addr = out_con_socket.accept()
    console.addline('Connection received.')
    t = ConsoleReceiveSocketThread(connection=conn,in_socket=in_con_socket,out_socket=out_con_socket,console=console)
    t.start()
    try:
        while console.readline():
            in_con_socket.sendall(console.input_string)
    except KeyboardInterrupt:
        #TODO: send disconnect command?
        console.addline('Disconnecting...')
        t.disconnect()
    finally:
        in_con_socket.close()
        out_con_socket.close()
        #TODO: timeout?
        t.join() 
        console.addline('Closed')
        os.unlink(OUT_CON_SOCKET_PATH)                  

if __name__ == '__main__':
    try:
        os.unlink(OUT_CON_SOCKET_PATH)
    except:
        pass
    curses.wrapper(main)
