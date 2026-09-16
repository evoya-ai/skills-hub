#!/usr/bin/env bash
# test-skill-repo.sh — tests for bin/skill-repo (lazy setup + attach command).
#
# Pure bash, no network: remotes are local file:// bare repos, the hub under
# test is a fixture copy of bin/skill-repo + sources.template.yml + meta/,
# and HOME is overridden so the global skill symlink + path file land in
# the fixture.
# All temp state lives under tests/.tmp/ (gitignored). The script wipes its
# case dirs on re-run; final leftovers stay for inspection (path is printed).
#
# Run from anywhere:  bash tests/test-skill-repo.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
TMP="$HERE/.tmp"

command -v git >/dev/null 2>&1 || { echo "git is required"; exit 1; }

# hermetic git (no user/system config), explicit identity
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com

PASS=0 FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ok  - $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL- $1"; }

canonical_dir() {
  (cd "$1" 2>/dev/null && pwd -P)
}

assert() { # $1=desc, rest: command expected to succeed
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi
}
assert_not() { # $1=desc, rest: command expected to fail
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then bad "$desc"; else ok "$desc"; fi
}
assert_no_match() { # $1=desc $2=text $3=regex that must NOT appear
  if printf '%s' "$2" | grep -qE -- "$3"; then bad "$1"; else ok "$1"; fi
}
assert_match() { # $1=desc $2=text $3=regex that MUST appear
  if printf '%s' "$2" | grep -qE -- "$3"; then ok "$1"; else bad "$1"; fi
}
no_entry() { # $1=sources file $2=name -> true if NO active entry for name
  ! grep -qE "^[[:space:]]*-[[:space:]]*name:[[:space:]]*$2[[:space:]]*$" "$1"
}
active_entries() { # $1=sources file -> count of active entries
  grep -cE '^[[:space:]]*-[[:space:]]*name:' "$1" || true
}

new_hub() { # $1=case name -> sets CASE/HUB, exports HOME
  CASE="$TMP/$1"
  rm -rf "$CASE"
  mkdir -p "$CASE/home" "$CASE/hub/bin" "$CASE/hub/meta"
  cp "$REPO/bin/skill-repo" "$CASE/hub/bin/"
  cp "$REPO/sources.template.yml" "$CASE/hub/"
  cp -R "$REPO/meta/skill-hub-handling" "$CASE/hub/meta/"
  export HOME="$CASE/home"
  HUB="$CASE/hub"
}

seed_remote() { # $1=bare repo path, $2=branch (default main) — one skill inside
  local bare="$1" branch="${2:-main}" work
  work="$TMP/.seed.$$.$RANDOM"
  rm -rf "$work"
  mkdir -p "$work/skills/marketing/data-table"
  printf -- '---\nname: data-table\ndescription: render tables nicely\n---\n\n# data-table\n\nBody.\n' \
    > "$work/skills/marketing/data-table/SKILL.md"
  git init -q -b "$branch" "$work"
  git -C "$work" add -A
  git -C "$work" commit -qm "content"
  rm -rf "$bare"
  git clone -q --bare "$work" "$bare"
  rm -rf "$work"
}

run_cli() { # args... -> OUT (stdout), ERR (stderr), RC (exit code)
  OUT="$(bash "$HUB/bin/skill-repo" "$@" 2>"$CASE/stderr")"; RC=$?
  ERR="$(cat "$CASE/stderr" 2>/dev/null || true)"
}

mkdir -p "$TMP"

# ---------------------------------------------------------------- tests

t1() {
  echo "T1  fresh setup: personal/ only, warning-free"
  new_hub t1
  run_cli setup
  assert "setup rc=0" test "$RC" = 0
  assert "personal/ is a git repo" test -d "$HUB/personal/.git"
  assert "no shared/ dir created" test ! -e "$HUB/shared"
  assert "sources.yml: exactly one active entry" test "$(active_entries "$HUB/sources.yml")" = 1
  assert "sources.yml: no active evoya entry" no_entry "$HUB/sources.yml" evoya
  run_cli search table
  assert "search rc=0" test "$RC" = 0
  assert_no_match "search stderr is warning-free" "$ERR" warning
}

t2() {
  echo "T2  setup --shared evoya=<url>: clone + register WITH remote"
  new_hub t2
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared "evoya=file://$CASE/remote.git"
  assert "setup rc=0" test "$RC" = 0
  assert "shared/evoya cloned" test -d "$HUB/shared/evoya/.git"
  assert "sources.yml records remote:" grep -qF "remote: file://$CASE/remote.git" "$HUB/sources.yml"
  run_cli search data-table
  assert "search finds data-table" grep -q "data-table" <<< "$OUT"
  run_cli update
  assert "update rc=0" test "$RC" = 0
  assert_no_match "update has no failures" "$ERR" failed
}

t3() {
  echo "T3  scaffold + attach: local == origin/main, upstream, remote recorded"
  new_hub t3
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared demo
  assert "scaffold created" test -d "$HUB/shared/demo/.git"
  assert "scaffold has no remote" test -z "$(git -C "$HUB/shared/demo" remote)"
  run_cli attach demo "file://$CASE/remote.git"
  assert "attach rc=0" test "$RC" = 0
  assert "origin set" test "$(git -C "$HUB/shared/demo" remote get-url origin)" = "file://$CASE/remote.git"
  assert "HEAD == origin/main" test "$(git -C "$HUB/shared/demo" rev-parse HEAD)" = "$(git -C "$CASE/remote.git" rev-parse main)"
  assert "upstream is origin/main" test "$(git -C "$HUB/shared/demo" rev-parse --abbrev-ref '@{u}')" = "origin/main"
  assert "sources.yml has remote:" grep -qF "remote: file://$CASE/remote.git" "$HUB/sources.yml"
  run_cli update
  assert "update rc=0" test "$RC" = 0
  assert_no_match "update has no failures" "$ERR" failed
  run_cli search data-table
  assert "search finds the attached skill" grep -q "data-table" <<< "$OUT"
}

t4() {
  echo "T4  attach vs real local commits: refuse, zero side effects"
  new_hub t4
  seed_remote "$CASE/remote.git" main
  run_cli setup
  mkdir -p "$HUB/shared/real/skills/x/realskill"
  printf -- '---\nname: realskill\ndescription: real\n---\n' > "$HUB/shared/real/skills/x/realskill/SKILL.md"
  git -C "$HUB/shared/real" init -q -b main
  git -C "$HUB/shared/real" add -A
  git -C "$HUB/shared/real" commit -qm one
  echo more >> "$HUB/shared/real/README.md"
  git -C "$HUB/shared/real" add -A
  git -C "$HUB/shared/real" commit -qm two
  run_cli attach real "file://$CASE/remote.git"
  assert "attach rc!=0" test "$RC" != 0
  assert "no origin added" test -z "$(git -C "$HUB/shared/real" remote)"
  assert "local commits intact" test "$(git -C "$HUB/shared/real" rev-list --count HEAD)" = 2
  assert "sources.yml: no 'real' entry" no_entry "$HUB/sources.yml" real
}

t5() {
  echo "T5  attach vs dirty scaffold: refuse, edit preserved"
  new_hub t5
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared demo
  echo "scratch note" >> "$HUB/shared/demo/README.md"
  run_cli attach demo "file://$CASE/remote.git"
  assert "attach rc!=0" test "$RC" != 0
  assert "no origin added" test -z "$(git -C "$HUB/shared/demo" remote)"
  assert "dirty edit preserved" grep -q "scratch note" "$HUB/shared/demo/README.md"
  assert_not "sources.yml has no remote: for demo" grep -qF "remote: file://$CASE/remote.git" "$HUB/sources.yml"
}

t6() {
  echo "T6  remote default branch 'trunk': local branch follows"
  new_hub t6
  seed_remote "$CASE/remote.git" trunk
  run_cli setup --shared demo
  run_cli attach demo "file://$CASE/remote.git"
  assert "attach rc=0" test "$RC" = 0
  assert "local branch renamed to trunk" test "$(git -C "$HUB/shared/demo" rev-parse --abbrev-ref HEAD)" = trunk
  assert "HEAD == origin/trunk" test "$(git -C "$HUB/shared/demo" rev-parse HEAD)" = "$(git -C "$CASE/remote.git" rev-parse trunk)"
  assert "upstream is origin/trunk" test "$(git -C "$HUB/shared/demo" rev-parse --abbrev-ref '@{u}')" = "origin/trunk"
}

t7() {
  echo "T7  attach twice: second refuses, nothing changes"
  new_hub t7
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared demo
  run_cli attach demo "file://$CASE/remote.git"
  assert "first attach rc=0" test "$RC" = 0
  run_cli attach demo "file://$CASE/other.git"
  assert "second attach rc!=0" test "$RC" != 0
  assert "origin unchanged" test "$(git -C "$HUB/shared/demo" remote get-url origin)" = "file://$CASE/remote.git"
}

t8() {
  echo "T8  attach personal (registered scaffold, remote has refs)"
  new_hub t8
  seed_remote "$CASE/remote.git" main
  run_cli setup
  run_cli attach personal "file://$CASE/remote.git"
  assert "attach rc=0" test "$RC" = 0
  assert "personal HEAD == origin/main" test "$(git -C "$HUB/personal" rev-parse HEAD)" = "$(git -C "$CASE/remote.git" rev-parse main)"
  assert "upstream is origin/main" test "$(git -C "$HUB/personal" rev-parse --abbrev-ref '@{u}')" = "origin/main"
  assert "sources.yml records remote: for personal" grep -qF "remote: file://$CASE/remote.git" "$HUB/sources.yml"
}

t9() {
  echo "T9  attach unregistered name, dir missing: clone + register"
  new_hub t9
  seed_remote "$CASE/remote.git" main
  run_cli setup
  run_cli attach newteam "file://$CASE/remote.git"
  assert "attach rc=0" test "$RC" = 0
  assert "shared/newteam cloned" test -d "$HUB/shared/newteam/.git"
  assert "registered with remote:" grep -qF "remote: file://$CASE/remote.git" "$HUB/sources.yml"
  run_cli search data-table
  assert "skill searchable under newteam" grep -q "newteam" <<< "$OUT"
}

t10() {
  echo "T10 attach to empty remote (no refs): refuse"
  new_hub t10
  rm -rf "$CASE/empty.git"
  git init -q --bare "$CASE/empty.git"
  run_cli setup --shared demo
  run_cli attach demo "file://$CASE/empty.git"
  assert "attach rc!=0" test "$RC" != 0
  assert_match "message explains missing refs" "$OUT$ERR" "no refs"
  assert_not "sources.yml has no remote: for demo" grep -qF "remote: file://$CASE/empty.git" "$HUB/sources.yml"
}

t11() {
  echo "T11 registered name with missing dir: refuse with hint"
  new_hub t11
  seed_remote "$CASE/remote.git" main
  run_cli setup
  printf '  - name: ghost\n    path: shared/ghost\n    root: skills\n' >> "$HUB/sources.yml"
  run_cli attach ghost "file://$CASE/remote.git"
  assert "attach rc!=0" test "$RC" != 0
  assert_match "hint mentions sources.yml" "$ERR" "sources.yml"
}

t12() {
  echo "T12 usage/help lists attach"
  new_hub t12
  run_cli --help
  assert "help rc=0" test "$RC" = 0
  assert "help lists attach" grep -q "attach" <<< "$OUT"
}

t13() {
  echo "T13 template: evoya is only a commented example"
  assert "no active evoya entry in template" no_entry "$REPO/sources.template.yml" evoya
  assert "personal is active in template" grep -qE '^[[:space:]]*-[[:space:]]*name:[[:space:]]*personal[[:space:]]*$' "$REPO/sources.template.yml"
}

t14() {
  echo "T14 link: plain names + .roo/skills/.gitignore, no root pattern"
  new_hub t14
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared "evoya=file://$CASE/remote.git"
  assert "setup rc=0" test "$RC" = 0
  proj="$CASE/proj"
  mkdir -p "$proj/.roo/skills"
  git init -q -b main "$proj"
  printf 'source: evoya\nskills:\n  - marketing/data-table\n' > "$proj/.roo/skills.yml"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  ERR="$(cat "$CASE/stderr" 2>/dev/null || true)"
  assert "link rc=0" test "$RC" = 0
  assert "plain-name symlink exists" test -L "$proj/.roo/skills/data-table"
  assert "no .hub name" test ! -e "$proj/.roo/skills/data-table.hub"
  assert "skills .gitignore entry" grep -qxF '/data-table' "$proj/.roo/skills/.gitignore"
  assert "skills .gitignore header" grep -qxF '# hub links — managed by skill-repo link' "$proj/.roo/skills/.gitignore"
  assert "root .gitignore untouched" test ! -e "$proj/.gitignore"
  assert "lock key is plain" grep -q '^data-table:$' "$proj/.roo/skills.lock"
  assert "no aliased field in lock" test -z "$(grep '^  aliased:' "$proj/.roo/skills.lock")"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  assert "relink rc=0" test "$RC" = 0
  assert "no duplicate entries" test "$(grep -c '^/data-table$' "$proj/.roo/skills/.gitignore")" = 1
  printf 'source: evoya\nskills: []\n' > "$proj/.roo/skills.yml"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  assert "empty-manifest relink rc=0" test "$RC" = 0
  assert "stale entry reconciled away" test -z "$(grep -x '/data-table' "$proj/.roo/skills/.gitignore")"
  assert "header survives reconcile" grep -qxF '# hub links — managed by skill-repo link' "$proj/.roo/skills/.gitignore"
  printf '/hand-written\n' > "$proj/.roo/skills/.gitignore"
  printf 'source: evoya\nskills:\n  - marketing/data-table\n' > "$proj/.roo/skills.yml"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  assert "headerless file: link rc=0" test "$RC" = 0
  assert "headerless file: entry appended" grep -qxF '/data-table' "$proj/.roo/skills/.gitignore"
  assert "headerless file: user line kept" grep -qxF '/hand-written' "$proj/.roo/skills/.gitignore"
}

t15() {
  echo "T15 manifest alias entry ('as') is rejected"
  new_hub t15
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared "evoya=file://$CASE/remote.git"
  assert "setup rc=0" test "$RC" = 0
  proj="$CASE/proj"
  mkdir -p "$proj/.roo/skills"
  git init -q -b main "$proj"
  printf 'source: evoya\nskills:\n  - marketing/data-table as tbl\n' > "$proj/.roo/skills.yml"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  ERR="$(cat "$CASE/stderr" 2>/dev/null || true)"
  assert "link rc!=0" test "$RC" != 0
  assert_match "message rejects aliases" "$OUT$ERR" "aliases are no longer supported"
}

t16() {
  echo "T16 verify: linked frontmatter name != folder name fails hard"
  new_hub t16
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared "evoya=file://$CASE/remote.git"
  assert "setup rc=0" test "$RC" = 0
  sed 's/^name: data-table$/name: renamed-table/' \
    "$HUB/shared/evoya/skills/marketing/data-table/SKILL.md" > "$CASE/SKILL.md"
  mv "$CASE/SKILL.md" "$HUB/shared/evoya/skills/marketing/data-table/SKILL.md"
  git -C "$HUB/shared/evoya" add -A
  git -C "$HUB/shared/evoya" commit -qm rename
  proj="$CASE/proj"
  mkdir -p "$proj/.roo/skills"
  git init -q -b main "$proj"
  printf 'source: evoya\nskills:\n  - marketing/data-table\n' > "$proj/.roo/skills.yml"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  assert "link rc=0" test "$RC" = 0
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" verify 2>"$CASE/stderr" )"; RC=$?
  ERR="$(cat "$CASE/stderr" 2>/dev/null || true)"
  assert "verify rc!=0" test "$RC" != 0
  assert_match "message names the mismatch" "$OUT$ERR" "frontmatter name 'renamed-table' != link name 'data-table'"
}

t17() {
  echo "T17 local skills untouched and never ignored"
  new_hub t17
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared "evoya=file://$CASE/remote.git"
  assert "setup rc=0" test "$RC" = 0
  proj="$CASE/proj"
  mkdir -p "$proj/.roo/skills/my-skill"
  printf -- '---\nname: my-skill\ndescription: local\n---\n' > "$proj/.roo/skills/my-skill/SKILL.md"
  git init -q -b main "$proj"
  printf 'source: evoya\nskills:\n  - marketing/data-table\n' > "$proj/.roo/skills.yml"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  assert "link rc=0" test "$RC" = 0
  assert "local dir still a real dir" test -d "$proj/.roo/skills/my-skill"
  assert "local dir not a symlink" test ! -L "$proj/.roo/skills/my-skill"
  assert "local skill not ignored" test -z "$(grep -x '/my-skill' "$proj/.roo/skills/.gitignore")"
  assert "git sees local skill as untracked" test -n "$(git -C "$proj" status --porcelain -- .roo/skills/my-skill)"
}

t18() {
  echo "T18 category + explicit skill overlap: resolved once, linked once"
  new_hub t18
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared "evoya=file://$CASE/remote.git"
  assert "setup rc=0" test "$RC" = 0
  proj="$CASE/proj"
  mkdir -p "$proj/.roo/skills"
  git init -q -b main "$proj"
  printf 'source: evoya\ncategories:\n  - marketing\nskills:\n  - marketing/data-table\n' > "$proj/.roo/skills.yml"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  assert "link rc=0" test "$RC" = 0
  assert "exactly one lock entry" test "$(grep -c '^data-table:$' "$proj/.roo/skills.lock")" = 1
  assert "gitignore entry not duplicated" test "$(grep -c '^/data-table$' "$proj/.roo/skills/.gitignore")" = 1
  assert "symlink is a single link" test "$(find "$proj/.roo/skills" -maxdepth 1 -name 'data-table' | awk 'END { print NR }')" = 1
}

t19() {
  echo "T19 same skill id from two sources: conflict, no link"
  new_hub t19
  seed_remote "$CASE/one.git" main
  seed_remote "$CASE/two.git" main
  run_cli setup --shared "evoya=file://$CASE/one.git" --shared "beta=file://$CASE/two.git"
  assert "setup rc=0" test "$RC" = 0
  proj="$CASE/proj"
  mkdir -p "$proj/.roo/skills"
  git init -q -b main "$proj"
  printf 'skills:\n  - evoya/marketing/data-table\n  - beta/marketing/data-table\n' > "$proj/.roo/skills.yml"
  OUT="$( cd "$proj" && bash "$HUB/bin/skill-repo" link 2>"$CASE/stderr" )"; RC=$?
  ERR="$(cat "$CASE/stderr" 2>/dev/null || true)"
  assert "link rc=2 (conflict)" test "$RC" = 2
  assert_match "message reports the double selection" "$OUT$ERR" "selected twice"
  assert "no link created" test ! -e "$proj/.roo/skills/data-table"
}

t21() {
  echo "T21 CLI guard: no bash >= 4-only syntax creeps back in"
  assert_not "no associative arrays" grep -nE 'local -A|declare -A|typeset -A' "$REPO/bin/skill-repo"
  assert_not "no case-folding expansions" grep -nE '\$\{[0-9A-Za-z_]+(,,|\^\^?)\}' "$REPO/bin/skill-repo"
  assert_not "no mapfile/readarray" grep -nE '\b(mapfile|readarray)\b' "$REPO/bin/skill-repo"
}

t20() {
  echo "T20 search lowercases the term without bash-4 syntax"
  new_hub t20
  seed_remote "$CASE/remote.git" main
  run_cli setup --shared "evoya=file://$CASE/remote.git"
  assert "setup rc=0" test "$RC" = 0
  run_cli search DATA-TABLE
  assert "uppercase term finds skill" grep -q "data-table" <<< "$OUT"
  run_cli search Table
  assert "mixed-case term finds skill" grep -q "data-table" <<< "$OUT"
}

t22() {
  echo "T22 global meta skill: symlink + path file, edits live without setup"
  new_hub t22
  seed_remote "$CASE/remote.git" main
  mkdir -p "$HOME/.roo/skills"
  ln -s "$HUB/meta/skill-hub-handling" "$HOME/.roo/skills/skill-hub-handling"  # legacy install
  run_cli setup --shared "evoya=file://$CASE/remote.git"
  assert "setup rc=0" test "$RC" = 0
  g="$HOME/.roo/skills/skill-hub-handling"
  assert "deployed as symlink" test -L "$g"
  assert "symlink targets the hub" test "$(canonical_dir "$g")" = "$HUB/meta/skill-hub-handling"
  assert "path file written" test "$(cat "$HUB/meta/skill-hub-handling/resources/skill-hub-path.txt")" = "$HUB"
  assert "path file reachable through symlink" test -f "$g/resources/skill-hub-path.txt"
  assert "SKILL.md references the path file" grep -qF 'resources/skill-hub-path.txt' "$g/SKILL.md"
  assert_not "no placeholder syntax left" grep -rqF '{{SKILL_HUB_ROOT}}' "$HUB/meta/skill-hub-handling"
  echo "t22 edit" >> "$HUB/meta/skill-hub-handling/SKILL.md"
  assert "template edit visible without setup" grep -qF "t22 edit" "$g/SKILL.md"
  echo "/wrong/path" > "$HUB/meta/skill-hub-handling/resources/skill-hub-path.txt"
  run_cli setup
  assert "re-run setup rc=0" test "$RC" = 0
  assert "path file rewritten" test "$(cat "$HUB/meta/skill-hub-handling/resources/skill-hub-path.txt")" = "$HUB"
  # interim-build migration: rendered copy dir (marker) -> symlink
  rm "$HOME/.roo/skills/skill-hub-handling"
  mkdir -p "$g"
  printf 'rendered from x by skill-repo setup' > "$g/.rendered-by-skill-repo"
  printf -- '---\nname: skill-hub-handling\ndescription: rendered\n---\n' > "$g/SKILL.md"
  run_cli setup
  assert "rendered copy migrated to symlink" test -L "$g"
  assert "migrated symlink targets the hub" test "$(canonical_dir "$g")" = "$HUB/meta/skill-hub-handling"
}

t23() {
  echo "T23 foreign global skill dir: kept without --force, replaced with it"
  new_hub t23
  g="$HOME/.roo/skills/skill-hub-handling"
  mkdir -p "$g"
  printf -- '---\nname: skill-hub-handling\ndescription: hand-made\n---\n' > "$g/SKILL.md"
  run_cli setup
  assert "setup rc=0 (warn only)" test "$RC" = 0
  assert_match "warns: not overwritten" "$ERR" "not overwritten"
  assert "hand-made copy kept" grep -qF "hand-made" "$g/SKILL.md"
  assert "still a real dir" test -d "$g" -a ! -L "$g"
  run_cli setup --force
  assert "setup --force rc=0" test "$RC" = 0
  assert "symlink installed" test -L "$g"
  assert "symlink targets the hub" test "$(canonical_dir "$g")" = "$HUB/meta/skill-hub-handling"
  assert "hand-made backup kept" test -n "$(find "$HOME/.roo/skills" -maxdepth 1 -name 'skill-hub-handling.pre-hub-*')"
}

t24() {
  echo "T24 hub .gitignore covers the machine-local path file (idempotent)"
  new_hub t24
  run_cli setup
  assert "plain fixture: no .gitignore created" test ! -e "$HUB/.gitignore"
  git init -q -b main "$HUB"
  run_cli setup
  assert "git-repo hub: line appended" grep -qxF "meta/skill-hub-handling/resources/skill-hub-path.txt" "$HUB/.gitignore"
  assert "exactly one line" test "$(grep -cxF "meta/skill-hub-handling/resources/skill-hub-path.txt" "$HUB/.gitignore")" = 1
  assert "path file ignored by git" test -z "$(git -C "$HUB" status --porcelain -- meta/skill-hub-handling/resources/skill-hub-path.txt)"
}

t1;  t2;  t3;  t4;  t5;  t6;  t7
t8;  t9;  t10; t11; t12; t13
t14; t15; t16; t17
t18; t19; t20; t21
t22; t23; t24

echo
echo "passed: $PASS  failed: $FAIL"
if [ "$FAIL" = 0 ]; then
  echo "all green"
  exit 0
fi
echo "artifacts kept under: $TMP   (inspect, then: rm -rf $TMP)"
exit 1
