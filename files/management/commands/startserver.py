# encoding: utf-8
import socket
import threading

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from core import ServerWorker

class Command(BaseCommand):
    args = '<poll_id poll_id ...>'
    help = 'Closes the specified poll for voting'
    option_list = BaseCommand.option_list + (
            make_option('--port',
                default=6987,
                help='Porta usada pelo servidor.'),
            make_option('--backlog',
                default=5,
                help='backlog.'),
            )

    def handle(self, *args, **options):
        port = options.get('port')
        backlog = int(options.get('backlog'))
        s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        s.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        s.bind( ( '', port ) )
        s.listen( backlog )
        self.accept(s)

    def accept(self, socket):
        while True:
            try:
                conn, addr = socket.accept()
                print 'connected from ', addr
                t = ServerWorker(conn, addr)
                t.start()
            except KeyboardInterrupt:
                break

