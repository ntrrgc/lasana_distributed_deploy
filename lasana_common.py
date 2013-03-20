# -*- encoding: utf-8 -*-

from fabric.api import run, task

@task
def set_hostname(name):
    run('echo %s > /etc/hostname' % name)
    run('hostname %s' % name)

@task
def get_ip_address():
    return run('hostname -I')
