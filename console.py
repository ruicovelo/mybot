import curses
from threading import Thread
import socket
import os


from asyncconsole import AsyncConsole




IN_CON_SOCKET_PATH = 'input_console_socket'
OUT_CON_SOCKET_PATH = 'output_console_socket'

try:
    os.unlink(OUT_CON_SOCKET_PATH)
except:
    pass

def handle_received_output(s,console):
    ''' To be run by a thread that waits for incoming data and sends it for display in a AsyncConsole object '''
    conn,addr = s.accept()
    while True:
        data = conn.recv(1024)
        if not data:
            break
        if console:
            console.addline(data)
    

def main(stdscr):
    console = AsyncConsole(stdscr)
    in_con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    in_con_socket.connect(IN_CON_SOCKET_PATH)
    out_con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    out_con_socket.bind(OUT_CON_SOCKET_PATH)
    out_con_socket.listen(1)

    t = Thread(target=handle_received_output,args=(out_con_socket,console,))
    t.start()
    
    while console.readline():
        if console.input_string == 'quit':
            break
        in_con_socket.sendall(console.input_string)
    in_con_socket.close()
    out_con_socket.close()                  



if __name__ == '__main__':
    curses.wrapper(main)