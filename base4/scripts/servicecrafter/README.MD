
### <span style="color: rgb(107, 166, 230); display: block; margin: 0 auto; text-align: center;">SERVICE CRAFTER</span>

###  Idea:
    Quickly create usable microservice in project ImpresaOne.

### Usage:
1. Create yaml file with basic informations about new service in <span style="color: rgb(107, 166, 230);">src/scripts/servicecrafter/inits</span> with {{name}}.yaml where name is new service name. 

```yaml
# path: src/scripts/servicecrafter/inits/sample.yaml

# This is a sample YAML configuration
name: sample
models:
    options # This is considered by default
    sampleModel # This is not implemented yet
```
2. Run python script for crafting service 
```python
python src/scripts/servicecrafter/craft.py -s sample
```
* Instead of sample here you write a service name. Same name you set for yaml file. In this case it will be 'sample'.
* At this point you will see new service in <span style="color: rgb(107, 166, 230);">src/services/
3. Register service
   * ###### register database in  src/config/db.yaml
```yaml
db: &db
port: ${DB_PORT}
host: ${DB_HOST}
user: ${DB_USER}
password: ${DB_PASSWORD}

db_sample: &db_sample # Add this
   <<: *db # Add this
   database: ${DB_SAMPLE} # Add this
  
tortoise: 
   connections:
     conn_sample: # Add this
       engine: 'tortoise.backends.asyncpg' # Add this
       credentials: *db_sample # Add this
             
   apps:
     sample: # Add this 
       models: # Add this
        - 'services.sample.models' # Add this 
     default_connection: 'conn_sample' # Add this
```
* ###### register service in src/config/services.yaml
```yaml
services:
  - tickets:
  - tenants:
  - bp:
  - attachments:
  - todo:
  - timesheet:
  - flow:
  - sendmail:
  - wiki:
  - sample: # Add this
```

* ###### register service in src/bin/gen.yaml
```yaml
services:

  - name: sample # Add this
    singular: sample # Add this
    gen: # Add this
      - models # Add this
      - schemas # Add this
```
* ###### register service in .env file
```text
DB_SAMPLE=${DB_NAME_PREFIX} # Add this

DATABASES=($DB_AERICH $DB_TICKETS $DB_BP $DB_TENANTS $DB_TPLSVC $DB_ATTACHMENTS $DB_TODO $DB_TIMESHEET $DB_FLOW $DB_SENDMAIL $DB_WIKI $DB_SAMPLE) # Add this here
SERVICES=("tickets" "bp" "tenants" "attachments" "todo" "timesheet" "flow" "sendmail" "wiki" "sample" ) # Add this here
```

For now this is a process of adding new service into project. We hope that some improvements are close. At this point you have new service included in project also in tests.

### IMPORTANT
Gen models before starting tests. :) Need to implement this. 