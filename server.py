#!/usr/bin/env python

import os
import socket
import struct
import sys
from threading import Lock, Thread


QUEUE_LENGTH = 10
SEND_BUFFER = 4096

#Fill songlist/song once and store
song_list = []
songs = []

# per-client struct
class Client:

    mode = -1 #Mode 0 - list, Mode 1 - play, Mode 2 Stop, Mode 3 Stream
    song_num = -1

    def __init__(self):
        self.lock = Lock()


def client_write(lock,client):
    #List
    f = open("music/{}".format(songs[0]), "r")
    f.close()
    while True:
        lock.acquire()
        try:
            if client.mode == 0:
                response = "RESPONSE\nResponse-type: list\nstatus: OK\nBody-length: {}\n\n{}\n\r\n".format(len(song_list),  "\n".join(song_list))
                client.conn.send(response)
                client.mode = -1
            #Play
            if client.mode == 1: 
                
                f.close()
                f = open("music/{}".format(songs[client.song_num-1]), "r")
                response = "RESPONSE\nResponse-type: play\nstatus: OK\nBody-length: 0\n\n\r\n"
                client.conn.send(response)
                client.mode = 3
                        
            #Stop
            if client.mode == 2:
                f.close()
                client.mode = -1
                response = "RESPONSE\nResponse-type: stop\nstatus: OK\nBody-length: 0\n\n\r\n"
                client.conn.send(response)
            #stream
            if client.mode == 3:
               data =  f.read(1000)
               response = "STREAM\nResponse-type: streaming\nsong-number: {}\nbody-length: 1000\nis-terminating: FALSE\n{}\n\r\n".format(client.song_num, data)
               client.conn.send(response)
               if (len(response) < 1090):
                    f.close()
                    client.mode = -1 # was a break
          
               
        finally:
            lock.release()
        


def client_read(lock,client):
    while True:
        message = client.conn.recv(SEND_BUFFER)

        if not message: 
            break
        lock.acquire() 
        try:
            if message.split()[4] in ['l', 'list']:
                print 'The user asked for list.'
                client.mode = 0           

            if message.split()[4] in ['p', 'play']:
                
                client.mode = 1
                client.song_num = int(message.split()[6])
                print 'The user asked to play:'

            if message.split()[4] in ['s', 'stop']:
                if client.mode == 3:
                    client.mode = 2
                print 'The user asked for stop.'
        finally:
            lock.release()
        

    client.conn.close()

def get_mp3s(musicdir):
    print("Reading music files...")
    i = 1

    for filename in os.listdir(musicdir):
        if not filename.endswith(".mp3"):
            continue

        #Store song metadata for future use.  You may also want to build
        # the song list once and send to any clients that need it.

        songs.append(filename)
        song_list.append(str(i) + "-------------"  + filename[:-4]  )
        i = i +1


    print("Found {0} song(s)!".format(len(songs)))


    return songs, song_list

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python server.py [port] [musicdir]")
    if not os.path.isdir(sys.argv[2]):
        sys.exit("Directory '{0}' does not exist".format(sys.argv[2]))

    port = int(sys.argv[1])
    songs, songlist = get_mp3s(sys.argv[2])
    threads = []

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    

    s.bind((host, port))
    s.listen(QUEUE_LENGTH)

    lock = Lock()
    while True:
        conn, address = s.accept()

        client  = Client()

        client.conn = conn

        t = Thread(target=client_read, args=(lock,client))
        threads.append(t)
        t.start()
        t = Thread(target=client_write, args=(lock,client))
        threads.append(t)
        t.start()
    s.close()


if __name__ == "__main__":
    main()
