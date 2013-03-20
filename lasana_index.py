# -*- encoding: utf-8 -*-

# sed() is broken!
import sed_monkeypatch
sed_monkeypatch.patch()

from fabric.api import sudo, env, task, cd, lcd, local, run, puts, \
                       put, execute, roles, settings
from fabric.contrib.files import upload_template, sed, contains, append, exists
from os import path
import re

from lasana_common import set_hostname, get_ip_address

@roles('index')
@task
def setup_index():
    set_hostname('s0')
    setup_dns()
    setup_sql()

@task
def setup_dns():
    # Install DNS server
    run('aptitude install -y bind9 bind9utils', pty=False)

    # bind directory permissions need to be modified in order for dynamic
    # updates to work
    run('chmod g+w /etc/bind')

    # Get IP address and charge it into context
    context = {
            'ip_address': get_ip_address(),
            }

    # Set up configuration files
    with cd('/etc/bind'):
        upload_template('named.conf.local', 'named.conf.local', context,
                use_jinja=True, template_dir='templates/dns_server')
        upload_template('db.lasa.nya', 'db.lasa.nya', context,
                use_jinja=True, template_dir='templates/dns_server')

    # Restart DNS server
    run('service bind9 restart', pty=False)

@task
def setup_sql():
    # Install PostgreSQL
    run('aptitude install -y postgresql')

    # Path to PostgreSQL cluster on this Debian version
    cluster = '/etc/postgresql/8.4/main'

    # Allow connections from the Internet
    sed(path.join(cluster, 'postgresql.conf'), 
            r"^#(listen_addresses = ').*('.*)$",
            r"\1%s\2" % '*')

    # Allow user 'lasana' to authenticate for 'lasana' db from any IPv4 address
    wanted_auth = ('host', 'lasana', 'lasana', '0.0.0.0/0', 'md5')
    if not contains(path.join(cluster, 'pg_hba.conf'), 
            '^\s*' + r'\s+'.join(["%s"]*5) % tuple(map(re.escape, wanted_auth)) + '\s*$',
            escape=False):
        append(path.join(cluster, 'pg_hba.conf'), '\t'.join(wanted_auth))
    else:
        puts('lasana is already allowed to login')

    # Restart PostgreSQL
    run('service postgresql restart', pty=False)

    # Create user and database
    sql_commands = [
            "create user lasana with login encrypted password 'cremosa';",
            "create database lasana "
                "with owner=lasana template=template0 "
                "encoding='utf-8' "
                "lc_collate='es_ES.utf8' lc_ctype='es_ES.utf-8';",
            "\connect lasana",
            "create table syncdb_mutex (); alter table syncdb_mutex owner to lasana;",
            "create table registernode_mutex (); alter table registernode_mutex owner to lasana;",
            ]
    run('su - postgres -c psql << EOF\n%s\nEOF' % '\n'.join(sql_commands))

@task
def register_node_in_dns(name, ip_address):
    dns_commands = [
            'update add %s.lasa.nya. 86400 IN A %s' % (name, ip_address),
            'update add lasa.nya. 86400 IN A %s' % (ip_address),
            'send',
            ]
    run('nsupdate -v -k /etc/bind/rndc.key << EOF\n%s\nEOF' %
            '\n'.join(dns_commands))
