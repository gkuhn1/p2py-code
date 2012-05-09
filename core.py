# encoding: utf-8
import os
import socket
import json
import threading
import time
import errno
from threading import Thread
from files.models import Index, Client
from datetime import datetime
from datetime import timedelta

class P2py(object):

    def __init__(self, socket):
        self.socket = socket
        self._log = 0

    def receive(self, conn=None, block=True, timeout=5):
        conn = conn or self.conn
        conn.setblocking(block)
        conn.settimeout(timeout)
        data = []
        cnt = 0
        tam = 1024
        while cnt < 100:
            try:
                cnt+=1
                d = conn.recv(tam)
                data.append(d)
                if not d or len(d) < tam:
                    break
            except:
                break
        # print 'received %s' % ''.join(data)
        if data:
            return self.jd(''.join(data))
        return {}
    def send(self, sock, data):
        sock.send(self.je(data))
    def close(self, sock):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except socket.error, e:
            if e.errno == 107:
                # conexão foi fechada na outra ponta.
                pass
        sock.close()
    def je(self, data):
        return json.dumps(data)
    def jd(self, data):
        return json.loads(data)
    def log(self, msg):
        if hasattr(self, '_log',) and self._log:
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
        self.addr = addr[0]
        self.port = addr[1]

    def run(self):
        '''
        Trata a mensagem recebida
        '''
        msg = self.receive()
        self.log(msg)
        command = msg['COMMAND'].lower()
        args = msg.get('ARGS', None)
        if hasattr(self, command):
            attr = getattr(self, command)
            attr(args)
        else:
            raise Exception('Command "%s" not found.' % command)
        self.conn.close()

    def active(self, *args):
        Client.objects.filter(ip=self.addr).update(dt_expiracao=datetime.now()+timedelta(minutes=3))
        Client.objects.filter(dt_expiracao=datetime.now()-timedelta(minutes=5)).delete()

    def shutdown(self, *args):
        Client.objects.filter(ip=self.addr).delete()

    def send_list(self, args):
        _files = args['FILES'] or []
        c = Client()
        c.ip = self.addr
        c.port = args['PORT']
        c.save()

        for arquivo in _files:
            i = Index()
            i.client = c
            i.filename = arquivo['FILE']
            i.size = arquivo['SIZE']
            i.save()

    def search(self, args):
        dargs = list(Index.objects.filter(
                    filename__icontains=args['WORD'],
                    client__dt_expiracao__gte=datetime.now(),
                ).exclude(client__ip=self.addr
                ).values('filename', 'client__ip', 'client__port', 'size'))

        data = self.je({'COMMAND': 'SEND_SEARCH',
                        'ARGS': dargs})
        self.conn.send(data)
        self.conn.close()

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
        self._log = 1
        self.host = host
        self.port = port
        self.listen = listen
        self.search_results = []
        self.pasta = './shared'
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
        except Exception, e:
            print e
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
                self.show_search_results()
            elif opcao == 3:
                self.do_send_file()
            elif opcao == -1:
                # Validações antes de sair
                print 'Sair'
            else:
                print 'Opção inválida'

    def draw_menu(self):
        op = raw_input('''
            1. Buscar
            2. Mostrar resultados da busca.
            3. Baixar arquivo.
           -1. Sair

            Forneça uma opção: 
            ''')
        try: op = int(op)
        except: op = 0
        return op

    def show_search_results(self):
        if not self.search_results:
            print 'Search results empty'
            return None

        print 'IDX | IP | Filename | Filesize'

        for idx in range(0,len(self.search_results)):
            print '%2i  | %s | %s | %s' % (idx+1,
                                self.search_results[idx]['client__ip'],
                                self.search_results[idx]['filename'][0:25],
                                self.search_results[idx]['size'])

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
            try:
                _file = open(os.path.join(self.pasta,f), 'r')
            except IOError, e:
                self.log('ERRO: %s' % e)
                data = {'STATUS': 'ERROR: %s' % e}
                conn.send(self.je(data))
            else:
                _size = os.path.getsize(_file.name)
                data = {'STATUS': 'OK',
                        'SIZE': str(_size)
                        }
                conn.send(self.je(data))
                ok = conn.recv(5)
                if ok == 'SEND!':
                    sent = 0L
                    read = 50000
                    while sent < _size:
                        try:
                            conn.send(_file.read(read))
                            sent += read
                        except socket.error, e:
                            if e.errno == errno.EPIPE:
                                self.log('Client desconectado')
                                break
                            else:
                                raise
                    self.log('sending file %s to %s' % (f, addr))
        else:
            self.log('COMMAND desconhecido: %s' % data)
        self.close(conn)

    def do_send_file(self):
        '''
        Envia o comando para buscar arquivo
        '''
        idx = int(raw_input('Informe o "idx" do arquivo: '))-1
        if idx not in range(0, len(self.search_results)):
            print 'IDX INVALIDO'
        else:
            _file = self.search_results[idx]
            s = self.connect(host=_file['client__ip'],
                             port=_file['client__port'])

            data = {'COMMAND': 'SEND_FILE', 'ARGS': {
                                        'FILE': _file['filename']}
                    }
            self.send(s, data)
            # recebe o tamanho
            s.settimeout(5)
            data = self.receive(s)
            if data['STATUS'] == 'OK':
                tamanho = int(data.get('SIZE', 0))
                self.log('Download total size: "%s"' % tamanho)
                s.send('SEND!')
                tam_recv = 1024
                f = open(os.path.join(self.pasta, _file['filename']+'_rec'), 'w')
                s.settimeout(1)
                total_received = 0
                while 1:
                    d = s.recv(tam_recv)
                    f.write(d)
                    t_received = len(d)
                    total_received += len(d)
                    self.log('received %s of %s' % (total_received, tamanho))
                    if t_received < tam_recv or t_received == tamanho:
                        self.log( 'break in %s' % total_received)
                        break

                self.log('file saved as "%s"' % f.name)
                f.close()
            else:
                print 'Arquivo não encontrado!'
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
            self.log(results)
            if 'ARGS' in results:
                self.search_results = results['ARGS']

            print '%s resultados para "%s"' % (len(self.search_results),
                                                word)
            self.close(s)

    def do_send_list(self):
        '''
        Envia a lista de arquivos do cliente
        '''
        PASTA = self.pasta
        if not os.path.isdir(PASTA):
            if not os.path.exists(PASTA):
                # cria a pasta com nenhum arquivo.
                os.mkdir(PASTA)

        files = os.listdir(PASTA)
        args = []
        for f in files:
            d = {
                'SIZE': os.path.getsize(os.path.join(PASTA, f)),
                'FILE': f,
                }
            args.append(d)

        s = self.connect()
        data = {'COMMAND': 'SEND_LIST',
                'ARGS': {'FILES': args, 'PORT': self.listen},
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
