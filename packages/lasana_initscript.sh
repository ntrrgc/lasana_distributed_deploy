#! /bin/sh
# /etc/init.d/lasana
#

# This is a really bad initscript.
# Don't use it in real projects. It can't even restart!

case "$1" in
  start)
    echo "Starting lasana"
    su - lasana -c /lasana/start.sh
    ;;
  stop)
    echo "Stopping lasana"
    su - lasana -c /lasana/stop.sh
    ;;
  *)
    echo "Usage: /etc/init.d/lasana {start|stop}"
    exit 1
    ;;
esac

exit 0
