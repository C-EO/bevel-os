#!/bin/zsh
# Run several serial commands in a row: tools/bvx.sh "key ctrl+esc" "key down" ...  (use "dump name" to save captures/name.png)
PY=~/.espressif/python_env/idf5.5_py3.12_env/bin/python
cd "$(dirname "$0")/.."
for c in "$@"; do
  if [[ "$c" == dump\ * ]]; then $PY tools/bv.py dump captures/${c#dump }.png >/dev/null
  elif [[ "$c" == sleep\ * ]]; then sleep ${c#sleep }
  else $PY tools/bv.py cmd "$c" 15 | grep -v '^@@OK' ; fi
done
