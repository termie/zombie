#!/bin/sh

#workon zombie
tmux new-session -s zombie -n shell -d
tmux -v new-window -t zombie -n world -d
tmux -v new-window -t zombie -n client -d

tmux send-keys -t zombie:shell "workon zombie"
tmux send-keys -t zombie:world "workon zombie"
tmux send-keys -t zombie:world "python ./world_server.py"

tmux attach
