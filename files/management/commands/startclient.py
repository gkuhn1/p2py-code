# encoding: utf-8
import socket
import json

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from core import ClientWorker

class Command(BaseCommand):
    help = 'Inicia um cliente'
    option_list = BaseCommand.option_list + (
            make_option('--connect',
                default='localhost:6987',
                help='Parametros para conexão: host:porta - Default: localhost:6987'),
            make_option('--listen',
                default=6988,
                help='Porta de escuta para transferencias de arquivos.'),
            )

    def handle(self, *args, **options):
        conn_opts = options.get('connect')
        listen = int(options.get('listen'))
        host, port = conn_opts.split(':')
        port = int(port)
        ClientWorker(host, port, listen)

