#!/bin/bash
cd /lasana
xargs kill < fcgi.pid
rm -r fcgi.pid
