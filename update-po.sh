#!/bin/bash
for filename in safeeyes/config/locale/*/LC_MESSAGES/safeeyes.po; do
    echo "$filename"
    msgmerge -U -N "$filename" safeeyes/config/locale/safeeyes.pot
    if [ -f "$filename~" ] ; then
        rm "$filename~"
    fi
done