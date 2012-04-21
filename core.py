# encoding: utf-8
import socket
import json
import threading

class P2py(object):

    def __init__(self, socket):
        self.socket = socket

    def je(self, data):
        return json.dumps(data)
    def jd(self, data):
        return json.loads(data)

class ServerWorker(P2py, threading.Thread):
    COMMANDS = {
        # Client commands
        'ACTIVE',
        'SHUTDOWN',
        'SEND_LIST',
        'SEARCH',
        'GET_FILE',
        'RETRIEVE_FILE',
    }
    def __init__(self, conn, addr, *args, **kwargs):
        threading.Thread.__init__(self)
        self.conn = conn
        self.addr = addr

    def receive(self):
        d = self.conn.recv(1024)
        data = []
        while d:
            data.append(d)
            d = self.conn.recv(1024)
        print 'received %s' % ''.join(data)
        return self.jd(''.join(data))

    def run(self):
        '''
        Trata a mensagem recebida
        '''
        msg = self.receive()
        command = msg['COMMAND'].lower()
        args = msg['ARGS']
        if hasattr(self, command):
            attr = getattr(self, command)
            attr(args)
        else:
            raise Exception('Command "%s" not found.' % command)

    def active(self, *args):
        pass
    def shutdown(self, *args):
        pass
    def send_list(self, *args):
        print 'SEND_LIST', args
    def search(self, *args):
        print 'SEARCH', args
    def get_file(self):
        pass
    def retrieve_file(self):
        pass

class ClientWorker(P2py):
    COMMANDS = {
        'SEND_SEARCH',
        'GET_FILE',
    }
    def connect(self):
        '''
        Cria um socket.
        Inicia uma conexão com o servidor.
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(( self.host, self.port))
        return s
    def close(self, sock):
        sock.shutdown(socket.SHUT_RDWR)
    def __init__(self, host, port, listen):
        self.host = host
        self.port = port
        self.listen = listen
        self.do_send_list()
        self.do_search()

    def do_search(self):
        '''
        Envia o comando de pesquisa
        '''
        s = self.connect()
        data = {'COMMAND': 'SEARCH', 'ARGS': {'WORD': 'mp3'}}
        self.send(s, data)
        self.close(s)

    def do_send_list(self):
        '''
        Envia a lista de arquivos do cliente
        '''
        s = self.connect()
        data = {'COMMAND': 'SEND_LIST',
                'ARGS': [{'size': '20mb', 'file': 'arq1'}]
               }
        self.send(s, data)
        self.close(s)

    def send(self, sock, data):
        sock.send(self.je(data))
