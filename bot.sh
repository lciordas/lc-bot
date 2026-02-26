#!/bin/bash
# Start/stop/status for the lc-bot Lichess bot (lichess-bot/ + lc-bot).
#
#   ./bot.sh start    launch detached (survives closing the terminal); rotates the log
#   ./bot.sh stop     stop the bot and its multiprocessing workers (orphaned workers
#                     hold Lichess connections and cause 429s on the next start)
#   ./bot.sh restart  stop, wait for Lichess's ~60s rate-limit window, start
#   ./bot.sh status   running or not, plus the last few INFO lines
#   ./bot.sh log      follow the log, INFO/WARNING lines only (no traceback spam)
#   ./bot.sh rawlog   follow the full log

BOT_DIR="$(cd "$(dirname "$0")/lichess-bot" && pwd)"
PIDFILE="$BOT_DIR/bot.pid"
LOG="$BOT_DIR/bot.log"
# Only matches workers from this venv.
WORKER_PATTERN="lichess-bot/.venv/bin/python -c from multiprocessing"

running() {
    [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

start() {
    if running; then
        echo "already running (pid $(cat "$PIDFILE"))"
        return 1
    fi
    # Another checkout may run a bot on the same Lichess account; two at once conflict.
    if pgrep -f "lichess-bot.py" >/dev/null; then
        echo "another lichess-bot is already running (pid $(pgrep -f lichess-bot.py | head -1))."
        echo "Stop it first (e.g. ./watchdog.sh stop; ./bot.sh stop in the other checkout)."
        return 1
    fi
    [ -f "$LOG" ] && mv "$LOG" "$LOG.prev"
    cd "$BOT_DIR" || exit 1
    nohup .venv/bin/python lichess-bot.py >> "$LOG" 2>&1 < /dev/null &
    echo $! > "$PIDFILE"
    echo "started (pid $!). Watch it with: $0 log"
}

stop() {
    if running; then
        kill "$(cat "$PIDFILE")" 2>/dev/null
    fi
    pkill -f "lichess-bot.py" 2>/dev/null
    sleep 2
    pkill -f "$WORKER_PATTERN" 2>/dev/null
    rm -f "$PIDFILE"
    echo "stopped"
}

status() {
    if running; then
        echo "running (pid $(cat "$PIDFILE"))"
    else
        echo "not running"
    fi
    [ -f "$LOG" ] && grep -E "INFO|WARNING" "$LOG" | grep -v "Refreshing" | tail -8
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; echo "waiting 75s for Lichess's rate-limit window to clear..."; sleep 75; start ;;
    status)  status ;;
    log)     tail -f "$LOG" | grep --line-buffered -E "INFO|WARNING" | grep --line-buffered -v "Refreshing" ;;
    rawlog)  tail -f "$LOG" ;;
    *)       echo "usage: $0 {start|stop|restart|status|log|rawlog}"; exit 1 ;;
esac
