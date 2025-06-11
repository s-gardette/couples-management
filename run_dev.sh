#!/bin/bash

# Kill any existing tmux session named "couples-management"
tmux kill-session -t couples-management 2>/dev/null || true

# Create a new tmux session named "couples-management" with the first window
tmux new-session -d -s couples-management -n main

# Split the window horizontally to create two panes
tmux split-window -h -t couples-management:main

# Start the backend in the left pane
tmux send-keys -t couples-management:main.0 'cd Backend && uv run run_server.py' Enter

# Start the frontend in the right pane
tmux send-keys -t couples-management:main.1 'cd Frontend && ./dev.sh' Enter

# Set pane titles for better visibility
tmux select-pane -t couples-management:main.0 -T "Backend"
tmux select-pane -t couples-management:main.1 -T "Frontend"

# Attach to the session
tmux attach-session -t couples-management 