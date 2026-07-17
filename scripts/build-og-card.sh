#!/usr/bin/env bash
# Render the social share card SVG to a 1200x630 PNG.
#
# Deps: librsvg (rsvg-convert) and a Helvetica/Arial-class sans font on the
# system (macOS ships both). Reproducible: same SVG in, same PNG out.
#
#   ./scripts/build-og-card.sh
#
# The source of truth is scripts/og-card.svg; edit that, then re-run this.
set -euo pipefail
cd "$(dirname "$0")/.."

rsvg-convert -w 1200 -h 630 scripts/og-card.svg -o img/og-card.png
echo "wrote img/og-card.png ($(du -h img/og-card.png | cut -f1))"
