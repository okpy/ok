usage() {
  local script="$1"
  local usage="$(grep '^##' "${script}" | sed 's/^##//')"

  printf "Usage: ${script}\n\n${usage}\n"
}

log() {
  local message="$1"
  local format="\033[1m\033[7m"
  local reset="\033[0m"

  echo -e "$(date)\t${format}${message}${reset}"
}

required_env() {
  local scriptname="$1"
  local envname="$2"

  if [ -z "${!envname}" ]; then
    echo "${envname} must be set" >&2
    usage "${scriptname}"
    exit 1
  fi
}

generate_password() {
  local length="$1"

  < /dev/urandom tr -dc '_A-Za-z0-9' | head -c"${length}"
}

get_dotenv() {
  local dotenvfile="$1"
  local variable="$2"

  grep "${variable}" "${dotenvfile}" | cut -d'=' -f2-
}

az_login() {
  if [ ! -f "/tmp/.azsetupscriptlogin" ]; then
    log "Connecting to Azure"
    if ! az login --service-principal -u "${SP_APP_ID}" -p "${SP_APP_KEY}" -t "${SP_TENANT_ID}"; then
      echo "Unable to connect to Azure" >&2
      exit 1
    fi
    az account set --subscription "${SP_SUBSCRIPTION_ID}"
    az configure --defaults group="${RESOURCE_GROUP_NAME}" location="${RESOURCE_GROUP_LOCATION}"
    touch "/tmp/.azsetupscriptlogin"
  fi
}
