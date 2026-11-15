#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null || ! python3 -c 'import sys; assert sys.version_info >= (3,11)' 2>/dev/null; then
 echo 'Python 3.11+ is required. Installation agent: install a compatible Python from an official source, then rerun this script.' >&2
 exit 1
fi
exec python3 -B install.py --setup "$@"
