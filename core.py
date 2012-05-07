# encoding: utf-8
import socket
import json
import threading
import time
from threading import Thread

class P2py(object):

    def __init__(self, socket):
        self.socket = socket

    def receive(self, conn=None, block=True):
        conn = conn or self.conn
        conn.setblocking(block)
        data = []
        cnt = 0
        while cnt < 100:
            try:
                cnt+=1
                d = conn.recv(1024)
                if not d:
                    break
                data.append(d)
            except:
                break
        # print 'received %s' % ''.join(data)
        if data:
            return self.jd(''.join(data))
        return ''
    def send(self, sock, data):
        sock.send(self.je(data))
    def close(self, sock):
        sock.shutdown(socket.SHUT_RDWR)
    def je(self, data):
        return json.dumps(data)
    def jd(self, data):
        return json.loads(data)
    def log(self, msg):
        print msg

class ServerWorker(P2py, threading.Thread):
    COMMANDS = [
        # Client commands
        'ACTIVE',
        'SHUTDOWN',
        'SEND_LIST',
        'SEARCH',
        'GET_FILE',
        'RETRIEVE_FILE',
    ]
    def __init__(self, conn, addr, *args, **kwargs):
        threading.Thread.__init__(self)
        self.conn = conn
        self.addr = addr

    def run(self):
        '''
        Trata a mensagem recebida
        '''
        msg = self.receive(block=False)
        command = msg['COMMAND'].lower()
        args = msg.get('ARGS', None)
        if hasattr(self, command):
            attr = getattr(self, command)
            attr(args)
        else:
            raise Exception('Command "%s" not found.' % command)
        self.conn.close()

    def active(self, *args):
        print 'ACTIVE', args
    def shutdown(self, *args):
        print 'SHUTDOWN', args
    def send_list(self, *args):
        print 'SEND_LIST', args
    def search(self, *args):
        print 'SEARCH', args
        dargs = [
            {'FILE': 'teste5.txt', 'IP': '10.1.1.1', 'SIZE':'10mb'},
            {'FILE': 'teste4.txt', 'IP': '10.1.1.1', 'SIZE':'10mb'},
            {'FILE': 'teste3.txt', 'IP': '10.1.1.1', 'SIZE':'10mb'},
            {'FILE': 'teste2.txt', 'IP': '10.1.1.1', 'SIZE':'10mb'},
            {'FILE': 'teste1.txt', 'IP': '10.1.1.1', 'SIZE':'10mb'},
        ]
        data = self.je({'COMMAND': 'SEND_SEARCH',
                        'ARGS': dargs})
        self.conn.send(data)
        print 'data sent'
        self.conn.close()
    def get_file(self):
        pass
    def retrieve_file(self):
        pass

class ClientWorker(P2py):
    COMMANDS = [
        'SEND_SEARCH',
        'GET_FILE',
        ]
    def connect(self, host=None, port=None):
        '''
        Cria um socket.
        Inicia uma conexão com o servidor.
        '''
        host = host or self.host
        port = port or self.port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(( host, port))
        return s
    def __init__(self, host, port, listen):
        self.host = host
        self.port = port
        self.listen = listen
        self.search_results = []
        self.max_listen = 5 # maximo de conexões
        self.act_listen = 0 # clientes conectados
        self.active_timeout = 60 # em segundos

        # Threads
        self.th_listen = Thread(target=self.start_listen)
        self.th_listen.start()
        self.th_active = Thread(target=self.keep_active)
        self.th_active.start()

        try:
            self.do_send_list()
            self.menu()
            # self.do_search()
        finally:
            self.do_shutdown()
            self.th_listen._Thread__stop()
            self.th_listen.join()
            self.th_active._Thread__stop()
            self.th_active.join()

        # from IPython.Shell import IPShellEmbed ; IPShellEmbed()()

    def menu(self):
        opcao = 0
        while opcao >= 0:
            opcao = self.draw_menu()
            if opcao == 1:
                self.do_search()
            elif opcao == 2:
                print 'Opção 2'
            elif opcao == 5:
                self.show_search_results()
            elif opcao == -1:
                # Validações antes de sair
                print 'Sair'
            else:
                print 'Opção inválida'

    def draw_menu(self):
        op = raw_input('''
            1. Buscar
            2. OP 02.
            5. Show result list.
           -1. Sair

            Forneça uma opção: 
            ''')
        try: op = int(op)
        except: op = 0
        return op

    def show_search_results(self):
        if not self.search_results:
            print 'Search results empty'

        for result in self.search_results:
            print '%s | %s | %s' % (result['IP'], result['FILE'],
                                    result['SIZE'])

    def start_listen(self):
        '''
        Cria uma thread para escutar conexões de outros clientes.
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', self.listen))
        self.log('starting listen on %s' % self.listen)

        try:
            while True:
                s.listen(1)
                conn, addr = s.accept()
                th = Thread(target=self.send_file, args=(conn,addr))
                th.start()
        finally:
            s.close()

    def send_file(self, conn, addr):
        data = self.receive(conn)
        if data['COMMAND'] == 'SEND_FILE':
            f = data['ARGS']['FILE']
            self.log('sending file %s to %s' % (f, addr))
        else:
            self.log('COMMAND desconhecido: %s' % data)
    def do_send_file(self):
        '''
        Envia o comando para buscar arquivo
        '''
        s = self.connect()
        data = {'COMMAND': 'SEND_FILE', 'ARGS': {'FILE': '/tmp/teste.txt'}}
        self.send(s, data)
        self.close(s)

    def do_search(self):
        '''
        Envia o comando de pesquisa
        '''
        word = raw_input('Palavra para consulta: ')
        if word:
            s = self.connect()
            data = {'COMMAND': 'SEARCH', 'ARGS': {'WORD': word}}
            self.send(s, data)
            results = self.receive(s)
            self.search_results = results['ARGS']
            self.close(s)

    def do_send_list(self):
        '''
        Envia a lista de arquivos do cliente
        '''
        s = self.connect()
        data = {'COMMAND': 'SEND_LIST',
                'ARGS': [{'SIZE': '20mb', 'FILE': 'arq1'}]
               }
        self.send(s, data)
        self.close(s)

    def keep_active(self):
        '''
        Envia o pacote de confirmação de atividade do cliente.
        '''
        while True:
            time.sleep(self.active_timeout)
            s = self.connect()
            data = {'COMMAND': 'ACTIVE'}
            self.send(s, data)
            self.close(s)

    def do_shutdown(self):
        '''
        Envia o pedido de shutdown para o servidor
        '''
        s = self.connect()
        data = {'COMMAND': 'SHUTDOWN'}
        self.send(s, data)
        self.close(s)
