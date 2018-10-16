#!/bin/bash
if test -z "$1"; then echo "username required"; exit 1; fi
if test -z "$2"; then echo "password required"; exit 2; fi
HASH=`echo -n "$2$1" | md5`
echo "ALTER USER $1 WITH ENCRYPTED PASSWORD 'md5$HASH';"
