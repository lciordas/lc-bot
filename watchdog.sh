#!/bin/bash
# Restarts the lc-bot Lichess bot if its process is gone. Start detached with:
#
#   nohup ./watchdog.sh >> lichess-bot/watchdog.log 2>&1 &
#
# Stop it with:  ./watchdog.sh stop
#
# Uses bot.sh stop/start so orphaned workers are reaped (they cause 429s on reconnect).

DIR="$(cd "$(dirname "$0")" && pwd)"
BOT="$DIR/bot.sh"
PIDFILE="$DIR/lichess-bot/bot.pid"
WPIDFILE="$DIR/lichess-bot/watchdog.pid"
CHECK_INTERVAL=60
# Wait out Lichess's ~60s rate-limit window before restarting, or it 429s.
RESTART_DELAY=75

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ "$1" = "stop" ]; then
    if [ -f "$WPIDFILE" ] && kill -0 "$(cat "$WPIDFILE")" 2>/dev/null; then
        kill "$(cat "$WPIDFILE")" && rm -f "$WPIDFILE"
        echo "watchdog stopped"
    else
        echo "watchdog not running"
    fi
    exit 0
fi

if [ "$1" = "status" ]; then
    if [ -f "$WPIDFILE" ] && kill -0 "$(cat "$WPIDFILE")" 2>/dev/null; then
        echo "watchdog running (pid $(cat "$WPIDFILE"))"
    else
        echo "watchdog not running"
    fi
    exit 0
fi

if [ -f "$WPIDFILE" ] && kill -0 "$(cat "$WPIDFILE")" 2>/dev/null; then
    log "watchdog already running (pid $(cat "$WPIDFILE")), exiting"
    exit 1
fi
echo $$ > "$WPIDFILE"
trap 'rm -f "$WPIDFILE"' EXIT

# Prevent idle sleep (which would suspend the bot mid-game) while the watchdog runs.
caffeinate -i -w $$ &
log "watchdog started (pid $$), checking every ${CHECK_INTERVAL}s; holding caffeinate -i"

while true; do
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        :
    else
        log "bot is DOWN -- cleaning up and restarting"
        "$BOT" stop >/dev/null 2>&1
        sleep "$RESTART_DELAY"
        "$BOT" start
        sleep 15
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            log "restart OK (pid $(cat "$PIDFILE"))"
        else
            log "restart FAILED -- will retry on next check"
        fi
    fi
    sleep "$CHECK_INTERVAL"
done
