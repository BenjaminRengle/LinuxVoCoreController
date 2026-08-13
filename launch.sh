#!/bin/sh
# Launches VoCoreController.py against a chosen sim, backgrounding the
# createsimshm helper first when the sim needs one to pre-size its /dev/shm
# segments.
#
# rFactor2/LMU's own SMMP plugin creates its shared memory directly (no
# helper needed - see RFactor2Data.py, which has always worked without one).
# Assetto Corsa's acpmf_physics/acpmf_static/acpmf_graphics segments need to
# be created and sized first, which is what simshmbridge's "acshm" binary
# does.
#
# acshm is started as an async ("&") command, so per POSIX shell rules it
# runs with SIGINT/SIGQUIT set to be ignored (this is meant to stop a
# Ctrl+C aimed at the foreground job from also killing background ones) -
# and that ignored disposition survives acshm's own exec(). So Ctrl+C alone
# won't stop it; the trap below explicitly kills it by PID with SIGTERM
# instead, which isn't in that auto-ignored set. That means the script
# itself has to stay alive to run the trap, so (unlike an earlier version
# of this script) it can't exec() into VoCoreController.py directly.
#
# Usage: ./launch.sh rf2|ac [extra VoCoreController.py args...]

set -e

SIMSHMBRIDGE_DIR="${SIMSHMBRIDGE_DIR:-/home/bazzite/Documents/developement/simshmbridge}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

sim="$1"
if [ -z "$sim" ]; then
    echo "Usage: $0 rf2|ac [extra VoCoreController.py args...]" >&2
    exit 1
fi
shift

acshm_pid=""
cleanup() {
    if [ -n "$acshm_pid" ]; then
        kill "$acshm_pid" 2>/dev/null || true
    fi
}
trap cleanup INT TERM EXIT

case "$sim" in
    rf2)
        # No shm pre-sizing helper for rf2 - the game's own SMMP plugin
        # creates /dev/shm/\$rFactor2SMMP_* itself.
        ;;
    ac)
        acshm="$SIMSHMBRIDGE_DIR/assets/acshm"
        if [ ! -x "$acshm" ]; then
            echo "error: $acshm not found or not executable (run 'make -f Makefile.ac' in $SIMSHMBRIDGE_DIR)" >&2
            exit 1
        fi
        echo "Starting $acshm in the background to size AC's /dev/shm segments..."
        "$acshm" &
        acshm_pid=$!
        ;;
    *)
        echo "error: unknown sim '$sim' (expected 'rf2' or 'ac')" >&2
        exit 1
        ;;
esac

python3 "$SCRIPT_DIR/VoCoreController.py" --sim "$sim" "$@"
