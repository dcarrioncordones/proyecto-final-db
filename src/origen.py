"""Procedencia por fuente, ligada a hashes de los CSV realmente analizados."""
from pathlib import Path
import datetime, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'data/procesados/proveniencia_fuentes.json'

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def registrar_fuente(motor,mode,filenames):
    records=json.loads(PATH.read_text()) if PATH.exists() else {}
    records[motor]={'mode':mode,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'hashes':{name:digest(ROOT/'data/procesados'/name) for name in filenames}}
    PATH.write_text(json.dumps(records,ensure_ascii=False,indent=2))

def estados_fuentes():
    records=json.loads(PATH.read_text()) if PATH.exists() else {}
    states={}
    for motor in ['sqlserver','oracle','mongodb']:
        record=records.get(motor,{'mode':'muestra','hashes':{}}).copy()
        if record.get('mode')=='base_de_datos':
            hashes=record.get('hashes',{})
            valid=bool(hashes) and all((ROOT/'data/procesados'/n).exists() and digest(ROOT/'data/procesados'/n)==v for n,v in hashes.items())
            if not valid: record['mode']='archivos_modificados'
        states[motor]=record
    return states
