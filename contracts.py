"""Strict JSON parsing and action field allowlists."""
import json

FIELDS={
 '/api/evaluate':{'listings','budget','kind','months','optional','known_only','sort'},
 '/api/export':{'listings','preferences','ids','format'},
 '/api/book':{'listing','key','consent'}, '/api/reconcile':{'key'},
 '/api/preferences':{'text'}, '/api/searches/save':{'name','preferences'},
 '/api/searches/delete':{'id'}, '/api/bookings/status':{'key'},
 '/api/bookings/events':{'key'}, '/api/bookings/cancel':{'key','consent'},
 '/api/collections/create':{'name','listings','provenance'},
 '/api/collections/load':{'id','version'}, '/api/collections/versions':{'id'},
 '/api/collections/revise':{'id','listings','provenance','expected_version'},
 '/api/collections/archive':{'id','archived'},
 '/api/collections/diff':{'id','before','after'},
 '/api/snapshots/save':{'name','listings','preferences'}, '/api/snapshots/load':{'id'},
}

def validate_fields(path,body):
    if path in FIELDS and set(body)-FIELDS[path]:
        raise ValueError('Unsupported request fields: '+', '.join(sorted(set(body)-FIELDS[path])))

def parse_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON field: '+key)
            result[key]=value
        return result
    def constant(value):raise ValueError('Nonfinite JSON numbers are not supported: '+value)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
