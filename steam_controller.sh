#/usr/bin/bash

HERE=$(dirname "$(readlink -f "$0")")

ARGS=(
  --package-id steam_controller
  --country-code CZ
  --webhook-url https://discord.com/api/webhooks/1501222968435413053/55LjL4buxVx66b8IMyRKq1jJNjyM25q4bVy1aVnfshft7_omnyWMX8yZrj0LTTchdA-l
  --role-id 1501231401444446229
)

(
  cd "$HERE"
  pipenv run python3 ./steam_hardware.py "${ARGS[@]}" "${@}"
)