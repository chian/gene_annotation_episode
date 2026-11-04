#!/bin/bash
~/dev_container/bin/App-MetaCATS https://p3.theseed.org/services/app_service/ ~/dev_container/modules/bvbrc_metacats/app_specs/MetaCATS.json ~/dev_container/modules/bvbrc_metacats/tests/$1.json 1> ~/dev_container/modules/bvbrc_metacats/tests/$1.out  2> ~/dev_container/modules/bvbrc_metacats/tests/$1.err
if [ $2 -gt 0 ]
then
    rm -r ./work ./stage
fi
echo $1