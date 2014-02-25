import curses
import socket
import os
from mythreading import ReceiveSocketThread
from asyncconsole import AsyncConsole
import cPickle
from commandtranslate import BotCommand
import sys 

CON_SOCKET_PATH = 'console_socket'

line_number = 0

class ConsoleReceiveSocketThread(ReceiveSocketThread):
    
    def __init__(self,socket,console):
        super(ConsoleReceiveSocketThread,self).__init__(processing_function=self.handle_received_output,connection=socket)
        self.console = console
        self.socket = socket
        
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
        if cmd.name == 'disconnect':
            self.disconnect()
            self.addline('Connection closed')
    
    def disconnect(self):
        self.stop()
        self.socket.close()

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
    global con_socket
    con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    con_socket.connect(CON_SOCKET_PATH)
    console.addline('Connected to server.')
    t = ConsoleReceiveSocketThread(socket=con_socket,console=console)
    t.start()
    try:
        while console.readline():
            con_socket.sendall(console.input_string)
    except KeyboardInterrupt:
        console.addline('Disconnecting...')
        con_socket.sendall('disconnect')
        t.disconnect()
    finally:
        con_socket.close()
        #TODO: timeout?
        t.join() 
        console.addline('Closed')

if __name__ == '__main__':
    curses.wrapper(main)
