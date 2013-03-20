# -*- encoding: utf-8 -*-
#
# Distributed Lasaña deploy script
#

from fabric.api import env, execute, task
from lasana_common import *
from lasana_node import *
from lasana_index import *

env.roledefs = {
    'index': ['192.168.4.2'],
    'node': ['192.168.4.3', '192.168.4.6', '192.168.4.20', '192.168.4.16'],
}

env.parallel = True

env.user = 'root'
env.password = 'bechamel'

@task(default=True)
def full_deploy():
    create_node_home_package()
    execute(setup_index)
    execute(setup_node, index=env.roledefs['index'][0])
