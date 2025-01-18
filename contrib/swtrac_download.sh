#!/usr/bin/env bash

script_home="$(dirname ${BASH_SOURCE:-$0} | xargs readlink -f)"
webdav_path=webdav/agent/log/
local_path=${SWTRAC_DOWNLOAD:-~/downloads/tmp/swtrac}

if [ ! -d ${local_path} ]; then
    echo Path does no exist ot is not directory: ${local_path}
    echo You may set SWTRAC_DOWNLOAD environment variable
    exit 1
fi

# това може и без него; паролата може да се въвежда за всяка команда;
# но така, ако е достъпно gpg, чрез неговия gpg-agent паролата за
# декриптиране на ключа се въвежда по-рядко
# gpg -er ddimitrov_admin -ao password
passwd_file=${local_path}/password
passwd=$(test -f ${passwd_file} -a -x /usr/bin/gpg && gpg -qd ${passwd_file})
if [ ! -z "$passwd" ]; then
  passwd="--password $passwd"
fi

export PYTHONUNBUFFERED=yes

case "$1" in
  list)
    davcli download \
           --davhost ${DAVCLI_WEBDAV_BASE_URL}\
           --user ddimitrov_admin $passwd \
           --swtrac-log-weeks 5 --pattern 'auth.*' \
           $webdav_path list
    ;;
  sync)
    davcli download \
           --davhost ${DAVCLI_WEBDAV_BASE_URL} \
           --user ddimitrov_admin $passwd \
           --swtrac-log-weeks 3 \
           $webdav_path sync $local_path --append

    davcli download \
           --davhost ${DAVCLI_WEBDAV_BASE_URL} \
           --user ddimitrov_admin $passwd \
           --pattern 'auth.*' \
           $webdav_path sync $local_path
    ;;
  *)
    echo "usage: $(basename $0) [list | sync]"
    exit 127
    ;;
esac

# vim:ft=sh:et:sw=2:ts=2
