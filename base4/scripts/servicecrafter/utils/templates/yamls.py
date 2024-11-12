OPTIONS_MODEL_TEMPLATE = """
option:
  __meta:
    table_name: {{ table_name }}
    app: {{ app }}


  key:
    field: "fields.CharField(255, null=False, unique=True)"

  value:
    field: "fields.TextField(null=True)"
"""


OPTIONS_SCHEMA_TEMPLATE = """
option:

  __schemas:
    all: OptionSchema

  key:
    mandatory: True
    type: str

  value:
    mandatory: True
    type: str

"""


INIT = """
name: {{ app }}

models:
  - {{ app }}

"""
