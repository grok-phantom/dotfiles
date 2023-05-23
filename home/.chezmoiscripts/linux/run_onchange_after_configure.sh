#!/bin/bash

set -eufo pipefail

sh ~/.vim_runtime/install_awesome_vimrc.sh

ln -s -f ~/.tmux/.tmux.conf ~/.tmux.conf
cp ~/.tmux/.tmux.conf.local ~
