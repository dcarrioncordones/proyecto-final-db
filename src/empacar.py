"""Prepara entrega, conserva proveniencia y excluye entornos y credenciales."""
from pathlib import Path
import hashlib, json, shutil, zipfile
ROOT=Path(__file__).resolve().parents[1]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def files():
    skip={'.venv','.mplcache','.jupyter','__pycache__','.git','.DS_Store','.env','entrega','captures'}
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and not skip.intersection(p.relative_to(ROOT).parts))

def main():
    sources={}
    for p in (ROOT/'data/original').glob('*.sql'):
        base='https://raw.githubusercontent.com/microsoft/sql-server-samples/master/samples/databases/northwind-pubs/' if p.name=='instnwnd.sql' else 'https://raw.githubusercontent.com/oracle-samples/db-sample-schemas/main/human_resources/'
        sources[p.name]={'url':base+p.name,'sha256':sha(p),'download_date':'2026-10-08'}
    (ROOT/'data/original/SOURCES.json').write_text(json.dumps(sources,indent=2))
    rows=[sha(p)+'  '+p.relative_to(ROOT).as_posix() for p in files() if p.name!='MANIFEST.sha256']
    (ROOT/'MANIFEST.sha256').write_text('\n'.join(rows)+'\n')
    out=ROOT/'entrega'; out.mkdir(exist_ok=True)
    pdfout=out
    target=pdfout/'Trabajo_final_Big_Data_Dan_Carrion.pdf'; shutil.copy2(ROOT/'informe/salida/Trabajo_final_Big_Data_Dan_Carrion.pdf',target)
    archive=out/'Proyecto_final_Big_Data.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in files(): z.write(p,'proyecto_final/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any('/.env'==n[-5:] or '/.jupyter/' in n or '/.venv/' in n for n in z.namelist())
        for line in rows:
            digest,path=line.split('  ',1)
            assert hashlib.sha256(z.read('proyecto_final/'+path)).hexdigest()==digest
        count=len(z.namelist())
    print(json.dumps({'pdf':str(target),'zip':str(archive),'files':count,'zip_bytes':archive.stat().st_size,'sha256_zip':sha(archive)},indent=2))

if __name__=='__main__': main()
