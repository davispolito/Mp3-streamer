#!/usr/bin/env python

import ao
import mad
import readline
import socket
import struct
import sys
import threading
from time import sleep


class mywrapper(object):
    def __init__(self):
        self.mf = None
        self.data = ""
        self.state = 0

    def read(self, size):
        result = self.data[:size]
        self.data = self.data[size:]
        return result


def recv_thread_func(wrap, cond_filled, sock):
    while True:
        cond_filled.acquire()
        try:
            message = sock.recv(1090) 

            if message.split()[2] == "list":
                print "\n".join(message.split("\n")[5:])


            if message.split()[2] == "streaming":
                leng = message.split()[6]

                dataList = message.splitlines(True)
                dataList = dataList[5:-1]
                data = "".join(dataList)
                data = data[:-1]
                wrap.data += data

                cond_filled.notify()

            if message.split()[2] == "stop":
                wrap.data = ""
                wrap.mf = None
                cond_filled.notify()
        finally:
                cond_filled.release()
        



def play_thread_func(wrap, cond_filled, dev):
    while True:
        cond_filled.acquire()
        cond_filled.wait()
        try:
            wrap.mf = mad.MadFile(wrap)
            while wrap.state == 1:
                buf = wrap.mf.read()
                if buf is None:
                    break
                dev.play(buffer(buf), len(buf))
            
        finally: 
            cond_filled.release()
       


def main():
    if len(sys.argv) < 3:
        print 'Usage: %s <server name/ip> <server port>' % sys.argv[0]
        sys.exit(1)
    wrap = mywrapper()

   
    cond_filled = threading.Condition()


    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((sys.argv[1], int(sys.argv[2])))


    recv_thread = threading.Thread(
        target=recv_thread_func,
        args=(wrap, cond_filled, sock)
    )
    recv_thread.daemon = True
    recv_thread.start()
    
    dev = ao.AudioDevice('pulse')
    play_thread = threading.Thread(
        target=play_thread_func,
        args=(wrap, cond_filled, dev)
    )
    play_thread.daemon = True
    play_thread.start()

  
    while True:
        line = raw_input('>> ')

        if ' ' in line:
            cmd, args = line.split(' ', 1)
        else:
            cmd = line

        message = ""

       
        if cmd in ['l', 'list']:
            message = "REQUEST\nclient-ip: {}\n request-type: list\n\n\r\n".format(sock.getsockname()[0])

        if cmd in ['p', 'play']:
            message = "REQUEST\nclient-ip: {}\nrequest-type: play\nsong-number: {}\n\n\r\n".format(sock.getsockname()[0], args)
            print 'The user asked to play:', args
            wrap.state = 1

        if cmd in ['s', 'stop']:
            message = "REQUEST\nclient-ip: {}\n request-type: stop\n\n\r\n".format(sock.getsockname()[0])
            print 'The user asked for stop.'
            wrap.data = ""
            wrap.mf = None
            wrap.state = 0

        if cmd in ['quit', 'q', 'exit']:
            sock.close()
            sys.exit(0)

        sock.send(message)

    sock.close()

if __name__ == '__main__':
    main()
