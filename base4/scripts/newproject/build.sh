#!/bin/bash

base64_encoded_data=$(base64 -i new-project.sh)

echo "$base64_encoded_data" > build.txt
scp build.txt websites.prod:/home/digital/websites/base4/project313.sh
rm build.txt

alias newproject='curl -sS https://dcadmin:123@base4.digitalcube.dev/project.sh | base64 --decode | bash -s --'
