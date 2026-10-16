#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
chmod u+x ./DeadlockToolbox
exec ./DeadlockToolbox --install
