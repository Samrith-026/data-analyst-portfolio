"""Validate PBIR against Microsoft's versioned schemas. Requires jsonschema.

Run after build.py. Retrieves only schemas from developer.microsoft.com.
This checks file contracts, not visual behavior or DAX engine semantics.
"""
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin
import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT=Path(__file__).resolve().parent
CACHE={}
def retrieve(uri):
    if not uri.startswith('https://developer.microsoft.com/json-schemas/'):
        raise ValueError('Unexpected schema host: '+uri)
    if uri not in CACHE:
        with urlopen(uri,timeout=30) as response: CACHE[uri]=json.load(response)
    return Resource.from_contents(CACHE[uri],default_specification=DRAFT7)

registry=Registry(retrieve=retrieve)
count=0
for path in sorted((ROOT/'Healthcare.Report').rglob('*')):
    if not path.is_file(): continue
    value=json.loads(path.read_text())
    uri=value.get('$schema')
    if not uri: continue
    schema=retrieve(uri).contents
    schema=dict(schema, **{'$id':uri})
    jsonschema.Draft7Validator(schema,registry=registry).validate(value)
    count+=1
validation_path=ROOT/'results/validation.json'
status=json.loads(validation_path.read_text())
status['pbir_schema_validation']=f'PASS: {count} files against Microsoft schemas'
validation_path.write_text(json.dumps(status,indent=2)+'\n')
print(status['pbir_schema_validation'])
