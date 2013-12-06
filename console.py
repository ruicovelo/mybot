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

def handle_received_output(data):
    global console
    global line_number
    # ugly hack that will be removed when a communication protocol is implemented
    # avoids extra line breaks
    cmd=cPickle.loads(data)
    if cmd.name == 'output':
        if cmd.arguments[-1:] == '\n':
            cmd.arguments=cmd.arguments[:-1]
        console.addline(cmd.arguments)
        line_number = line_number+1
        return
    if cmd.name == 'quit':
        sys.exit()

def main(stdscr):
    global console
    console = AsyncConsole(stdscr)
    # This is clumsy and will sometimes fail; server might be faster to connect back 
    # before we have a socket ready
    # This will be fixed when we implement a communication protocol
    in_con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    in_con_socket.connect(IN_CON_SOCKET_PATH)
    out_con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    out_con_socket.bind(OUT_CON_SOCKET_PATH)
    out_con_socket.listen(1)
    console.addline('Connected to server. Waiting for server to connect back to client...')
    conn,addr = out_con_socket.accept()
    console.addline('Connection received.')
    t = ReceiveSocketThread(processing_function=handle_received_output,connection=conn)
    t.start()
    try:
        while console.readline():
            in_con_socket.sendall(console.input_string)
    except KeyboardInterrupt:
        pass
    finally:
        in_con_socket.close()
        out_con_socket.close()
        os.unlink(OUT_CON_SOCKET_PATH)                  

if __name__ == '__main__':
    try:
        os.unlink(OUT_CON_SOCKET_PATH)
    except:
        pass
    curses.wrapper(main)
