#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0
#
# Fails if a non-merge commit in BASE..HEAD has no Signed-off-by trailer.
# Commits by [bot] accounts, such as Dependabot, are skipped.
#   dco.sh BASE HEAD
set -euo pipefail
base=$1
head=$2
missing=0
for commit in $(git rev-list --no-merges "$base..$head"); do
  if [[ $(git log -1 --format=%an "$commit") == *"[bot]" ]]; then
    continue
  fi
  if ! git log -1 --format='%(trailers:key=Signed-off-by,valueonly)' "$commit" | grep -q .; then
    echo "::error::Commit $commit has no Signed-off-by line. See CONTRIBUTING.md: commit with git commit -s."
    missing=1
  fi
done
exit "$missing"
