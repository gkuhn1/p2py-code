# encoding: utf-8

from django.db import models
from datetime import timedelta, datetime

class Client(models.Model):

    ip = models.CharField('IP',
                          max_length=15)

    dt_expiracao = models.DateTimeField(
                    default=lambda: datetime.now()+timedelta(minutes=3))


    def __unicode__(self):
        return self.ip

class Index(models.Model):

    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    filename = models.CharField('Filename',
                            max_length=1000)

    size = models.CharField('Size',
                            max_length=20)

    def __unicode__(self):
        return self.filename
