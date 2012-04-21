# encoding: utf-8

from django.db import models

class Index(models.Model):

    ip = models.CharField('IP',
                          max_length=15)
    filename = models.CharField('Filename',
                            max_length=1000)
    size = models.CharField('Size',
                            max_length=20)

    def __unicode__(self):
        return self.filename
