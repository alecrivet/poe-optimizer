#!/usr/bin/env bash
# Claude Code status line for poe-optimizer
# Shows: dir | git branch | python venv | model | context % | vim mode

input=$(cat)

# --- extract fields from JSON ---
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
model=$(echo "$input" | jq -r '.model.display_name // ""')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
vim_mode=$(echo "$input" | jq -r '.vim.mode // empty')

# --- directory: basename only ---
dir=$(basename "$cwd")

# --- git branch (skip optional lock, silent on failure) ---
git_branch=""
if git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1; then
  git_branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null \
    || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
fi

# --- python venv indicator ---
venv_indicator=""
if [ -f "$cwd/.venv/pyvenv.cfg" ]; then
  py_ver=$(grep '^version' "$cwd/.venv/pyvenv.cfg" 2>/dev/null | head -1 | awk '{print $3}')
  venv_indicator="py${py_ver}"
fi

# --- context usage bar ---
context_str=""
if [ -n "$used_pct" ]; then
  used_int=${used_pct%.*}
  if [ "$used_int" -ge 80 ] 2>/dev/null; then
    context_str="ctx:${used_int}%(!)"
  else
    context_str="ctx:${used_int}%"
  fi
fi

# --- vim mode ---
vim_str=""
if [ -n "$vim_mode" ]; then
  vim_str="[$vim_mode]"
fi

# --- assemble parts ---
parts=()

# directory + git branch
if [ -n "$git_branch" ]; then
  parts+=("${dir}(${git_branch})")
else
  parts+=("$dir")
fi

# venv
[ -n "$venv_indicator" ] && parts+=("$venv_indicator")

# model (shortened)
if [ -n "$model" ]; then
  parts+=("$model")
fi

# context
[ -n "$context_str" ] && parts+=("$context_str")

# vim mode
[ -n "$vim_str" ] && parts+=("$vim_str")

# --- render with ANSI dim colors ---
output=""
sep=" | "
for i in "${!parts[@]}"; do
  if [ $i -eq 0 ]; then
    # directory+branch: bold white
    output+=$(printf '\033[1m%s\033[0m' "${parts[$i]}")
  elif [[ "${parts[$i]}" == py* ]]; then
    # python venv: yellow
    output+=$(printf '\033[33m%s\033[0m' "${parts[$i]}")
  elif [[ "${parts[$i]}" == ctx:* && "${parts[$i]}" == *"(!)" ]]; then
    # high context usage: red
    output+=$(printf '\033[31m%s\033[0m' "${parts[$i]}")
  elif [[ "${parts[$i]}" == ctx:* ]]; then
    # normal context: cyan
    output+=$(printf '\033[36m%s\033[0m' "${parts[$i]}")
  elif [[ "${parts[$i]}" == "["* ]]; then
    # vim mode: magenta
    output+=$(printf '\033[35m%s\033[0m' "${parts[$i]}")
  else
    # model: default dim
    output+=$(printf '\033[2m%s\033[0m' "${parts[$i]}")
  fi
  if [ $i -lt $(( ${#parts[@]} - 1 )) ]; then
    output+=$(printf '\033[2m%s\033[0m' "$sep")
  fi
done

printf '%s' "$output"
