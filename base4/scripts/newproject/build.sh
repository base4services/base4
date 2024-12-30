#!/bin/bash

# new-project script
base64_encoded_data=$(base64 -i new-project.sh)
echo "$base64_encoded_data" > build.txt
scp build.txt websites.prod:/home/digital/websites/base4/project.sh
rm build.txt

# init-project script
base64_encoded_data=$(base64 -i init-project.sh)
echo "$base64_encoded_data" > build.txt
scp build.txt websites.prod:/home/digital/websites/base4/init-project.sh
rm build.txt



