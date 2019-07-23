#!/usr/bin/env bash

rsync -v -e "ssh -i $HOME/.ssh/netsys1.pem" admin@$1:~/resource-lending
