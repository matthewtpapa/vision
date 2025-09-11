#!/usr/bin/env sh
set -eu

if git ls-files -z | grep -z -Ev '^docs/adr/|^docs/.*/adr/|^\.github/' | \
    xargs -0 -r grep -nEI -i 'runtime[[:space:]_]*ris|ris_runtime'; then
    echo >&2 "error: found banned runtime RIS tokens outside ADR"
    exit 1
fi

exit 0
