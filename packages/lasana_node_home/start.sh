#!/bin/bash
cd /lasana
source env/bin/activate
python manage.py runfcgi method=threaded socket=$PWD/fcgi.socket pidfile=$PWD/fcgi.pid umask=007
chmod 600 fcgi.pid
