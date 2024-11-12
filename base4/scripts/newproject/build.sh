#!/bin/bash

base64_encoded_data=$(base64 new-project.sh)

echo "$base64_encoded_data" > temp_file.txt
scp temp_file.txt websites.prod:/home/digital/websites/base4/project2.sh
rm temp_file.txt

#alias newproject='curl -sS https://dcadmin:123@base4.digitalcube.dev/project.sh | base64 --decode | bash -s --'
