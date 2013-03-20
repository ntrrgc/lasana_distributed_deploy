# -*- encoding: utf-8 -*-

from fabric.api import sudo, env, task, cd, lcd, local, run, puts, \
                       put, execute, roles, serial, settings
from fabric.contrib.files import upload_template, sed, contains, append, exists
from os import path
import re

from lasana_common import get_ip_address, set_hostname
from lasana_index import register_node_in_dns

@task 
def create_node_home_package():
    with lcd('packages/lasana_node_home'):
        local('GLOBIGNORE=". .."; tar zcfvp ../lasana_node_home.tar.gz * .*')

@task
def setup_lighttpd():
    # Install lighttpd
    run('aptitude install -y --without-recommends lighttpd', pty=False)

    # Upload configuration file
    put('packages/lasana_node_lighttpd/lighttpd.conf', '/etc/lighttpd/lighttpd.conf')

    # Restart lighttpd
    run('service lighttpd restart', pty=False)

@roles('node')
@task
def create_lasana_user():
    with settings(warn_only=True):
        ret = run('useradd --system --home-dir /lasana -g www-data lasana')
    if ret.return_code not in (0, 9): #do not raise if user exists
        raise SystemError

    # Create home and assign permissions
    run('mkdir -p /lasana -m 750')
    run('chown lasana:www-data /lasana')

def suprun(command, virtualenv='/lasana/env/bin/activate', umask=0077, user='lasana'):
    return sudo('umask %#03o && source %s && %s' % (umask, virtualenv, command), user=user)

@roles('node')
@task
def setup_node(index):
    if not path.exists('packages/lasana_node_home.tar.gz'):
        raise Exception('lasana_node_home.tar.gz does not exist. Run fab create_node_home_package first.')

    # Install lasaña dependencies
    run('aptitude install -y --without-recommends python-{virtualenv,psycopg2,flup} sudo git gettext', pty=False)

    # Create new user
    create_lasana_user()

    # Upload home
    put('packages/lasana_node_home.tar.gz', '/lasana/home.tar.gz')
    with cd('/lasana'):
        # Uncompress home
        sudo('tar zxfvp home.tar.gz', user='lasana')
        run('rm home.tar.gz')

        # Create a virtualenv
        sudo('umask 077; virtualenv --setuptools env', user='lasana')

        # Install Django and other requirements
        suprun('pip install -r requirements.txt')

        if not exists('lasana'):
            # Download lasaña repo from git
            suprun('git clone git://github.com/ntrrgc/lasana.git -b distributed')
        else:
            # Update lasaña repo
            with cd('lasana'): suprun('git pull')

        # Git version of lasaña requires compiling some things
        with cd('lasana'):
            # Compile messages (translations)
            suprun('django-admin.py compilemessages')

        # Collect static resources
        suprun('python manage.py collectstatic --noinput', umask=0027)

        # Sync database
        suprun('python manage.py synchronized_syncdb')

        # Register node in the database, getting a node Id
        suprun('python manage.py registernode')

        # Get node name from node Id
        node_name = 's' + run('cat nodeid')

        # Set hostname to the given node name
        set_hostname(node_name) # get only the subdomain part

    # Install lasaña initscript
    put('packages/lasana_initscript.sh', '/etc/init.d/lasana')
    run('chmod +x /etc/init.d/lasana')
    # Set it to boot with the system
    run('update-rc.d lasana defaults')

    # Start lasaña
    run('/etc/init.d/lasana start', pty=False)

    # Install and configure the web server
    setup_lighttpd()

    # Register the new name in DNS server
    execute(register_node_in_dns, node_name, get_ip_address(), hosts=[index])
