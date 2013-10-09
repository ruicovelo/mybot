import curses
import socket
import os
from mythreading import ReceiveSocketThread
from asyncconsole import AsyncConsole

IN_CON_SOCKET_PATH = 'in_console_socket'
OUT_CON_SOCKET_PATH = 'out_console_socket'
line_number = 0

def handle_received_output(data):
    global console
    console.addline('%d %s' % (line_number,data))
    line_number = line_number+1

def main(stdscr):
    global console
    console = AsyncConsole(stdscr)
    in_con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    in_con_socket.connect(IN_CON_SOCKET_PATH)
    out_con_socket = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    out_con_socket.bind(OUT_CON_SOCKET_PATH)
    out_con_socket.listen(1)
    conn,addr = out_con_socket.accept()
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
