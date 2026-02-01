#!/bin/bash

PROJECT_DIR="/home/ubuntu/bharati-data-extractor"
LOG_DIR="$PROJECT_DIR/logs"
JOBDIR="$PROJECT_DIR/crawls/knowledge-resume-1"

mkdir -p "$LOG_DIR"

ERROR_LOG="$LOG_DIR/error.log"
RESTART_LOG="$LOG_DIR/restart.log"
HEARTBEAT_FILE="$LOG_DIR/heartbeat.txt"

cd "$PROJECT_DIR"

monitor_activity() {
    while true; do
        sleep 300  # check every 5 minutes

        if [ -f "$HEARTBEAT_FILE" ]; then
            last=$(stat -c %Y "$HEARTBEAT_FILE")
            now=$(date +%s)
            diff=$((now - last))

            # Hang detection = 15 minutes (900 sec)
            if [ $diff -gt 900 ]; then
                echo "Hang detected at $(date). Killing spider..." >> "$RESTART_LOG"
                pkill -f "scrapy crawl knowledge"
            fi
        fi
    done
}

while true; do
    echo "Starting crawler at $(date)" >> "$RESTART_LOG"

    monitor_activity &
    MONITOR_PID=$!

    scrapy crawl knowledge         -s JOBDIR="$JOBDIR"         -s LOG_LEVEL=ERROR         > "$ERROR_LOG" 2>&1 &

    SCRAPY_PID=$!

    # Heartbeat updater
    while kill -0 $SCRAPY_PID 2>/dev/null; do
        date +%s > "$HEARTBEAT_FILE"
        sleep 120
    done

    kill $MONITOR_PID 2>/dev/null

    echo "Scraper stopped/crashed at $(date). Restarting in 30 sec..." >> "$RESTART_LOG"
    sleep 30
done
