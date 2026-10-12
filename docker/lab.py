"""Operaciones explícitas sobre el laboratorio bigdata-final; no toca otros proyectos."""
from pathlib import Path
import argparse, datetime, json, os, re, secrets, shlex, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
ENVFILE=ROOT/'docker/.env'
MOTORS=['sqlserver','oracle','mongodb']
SQL_TOOL='tool=/opt/mssql-tools18/bin/sqlcmd; [ -x "$tool" ] || tool=/opt/mssql-tools/bin/sqlcmd; SQLCMDPASSWORD="$MSSQL_SA_PASSWORD" "$tool"'
NW_COUNTS={'Orders':830,'Order Details':2155,'Customers':91,'Products':77,'Categories':8,'Suppliers':29,'Employees':9}
HR_COUNTS={'employees':107,'departments':27,'locations':23,'countries':25,'regions':5,'jobs':19,'job_history':10}

def configuration():
    if not ENVFILE.exists(): raise RuntimeError('Primero ejecuta: python3 docker/lab.py configurar')
    config={}
    for line in ENVFILE.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key,value=line.split('=',1); config[key.strip()]=value.strip().strip('"').strip("'")
    for key in ['SQL_PASSWORD','ORACLE_PASSWORD','HR_PASSWORD','MONGO_PASSWORD']:
        value=config.get(key,'')
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{11,63}',value) or value.startswith('CAMBIAR'):
            raise RuntimeError(key+': usa de 12 a 64 caracteres, iniciando con letra; sólo letras, números, _ o -.')
        if not all([re.search(r'[A-Z]',value),re.search(r'[a-z]',value),re.search(r'[0-9]',value)]):
            raise RuntimeError(key+': incluye mayúscula, minúscula y número.')
    if config.get('MSSQL_ACCEPT_EULA')!='Y': raise RuntimeError('Revisa la licencia de Microsoft y configura MSSQL_ACCEPT_EULA=Y si la aceptas.')
    return config

def redact(text):
    if ENVFILE.exists():
        for line in ENVFILE.read_text().splitlines():
            if '=' in line:
                key,value=line.split('=',1)
                if key.endswith('PASSWORD') and value: text=text.replace(value.strip(),'[oculto]')
    return text

def compose(args,input_text=None,quiet=False):
    configuration()
    command=['docker','compose','--env-file',str(ENVFILE),'-f',str(ROOT/'docker/compose.yaml'),'--profile','analisis',*args]
    result=subprocess.run(command,cwd=ROOT,input=input_text,text=True,capture_output=True)
    output=redact(result.stdout+result.stderr)
    if not quiet and output.strip(): print(output,end='' if output.endswith('\n') else '\n')
    if result.returncode: raise RuntimeError('La operación Docker falló. '+output.strip() if quiet else 'La operación Docker falló; revisa el mensaje anterior.')
    return result.stdout

def configure():
    if ENVFILE.exists():
        configuration(); print('docker/.env ya existe y es válido; se conserva.'); return
    credentials={'MSSQL_ACCEPT_EULA':'Y'}
    for key,prefix in [('SQL_PASSWORD','Sql'),('ORACLE_PASSWORD','Ora'),('HR_PASSWORD','Hr'),('MONGO_PASSWORD','Mon')]: credentials[key]=prefix+'_'+secrets.token_hex(16)+'9'
    text='# Contraseñas locales de laboratorio. No incluir en la entrega.\n'+'\n'.join(k+'='+v for k,v in credentials.items())+'\n'
    fd=os.open(ENVFILE,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f: f.write(text)
    print('Creado docker/.env con cuatro contraseñas distintas. No se muestran en pantalla.')

def sql(query,database='master'):
    cmd=SQL_TOOL+' -S localhost -U sa -C -b -h -1 -W -d '+shlex.quote(database)+' -Q '+shlex.quote('SET NOCOUNT ON; '+query)
    return compose(['exec','-T','sqlserver','sh','-c',cmd],quiet=True).strip()

def oracle(query,hr=False):
    # Conexión administrativa local por autenticación del sistema operativo.
    script='WHENEVER SQLERROR EXIT FAILURE\nWHENEVER OSERROR EXIT FAILURE\nSET ECHO OFF VERIFY OFF FEEDBACK OFF HEADING OFF PAGESIZE 0\n'
    if not hr: script+='ALTER SESSION SET CONTAINER=FREEPDB1;\n'
    script+=query+'\nEXIT\n'
    return compose(['exec','-T','oracle','sqlplus','-L','-s','/','as','sysdba'],input_text=script,quiet=True).strip()

def load_sql():
    exists=sql("SELECT CASE WHEN DB_ID(N'Northwind') IS NULL THEN 0 ELSE 1 END;")
    if exists=='1':
        objects=int(sql('SELECT COUNT(*) FROM sys.tables;','Northwind'))
        if objects:
            try: counts={table:int(sql('SELECT COUNT(*) FROM dbo.['+table+'];','Northwind')) for table in NW_COUNTS}
            except RuntimeError: raise RuntimeError('Northwind contiene objetos distintos. Se conserva; usa un laboratorio nuevo para cargar la muestra.')
            if counts!=NW_COUNTS: raise RuntimeError('Northwind ya tiene datos que difieren de la muestra o está incompleta. Se conserva; no se reinstala automáticamente.')
            print('Northwind ya contiene las siete tablas con los conteos esperados; se conserva.'); return
    else: sql('CREATE DATABASE Northwind;')
    # El script oficial recrea objetos: sólo se ejecuta cuando la base está vacía.
    cmd=SQL_TOOL+' -S localhost -U sa -C -b -d Northwind -i /datasets/instnwnd.sql'
    compose(['exec','-T','sqlserver','sh','-c',cmd])
    counts={table:int(sql('SELECT COUNT(*) FROM dbo.['+table+'];','Northwind')) for table in NW_COUNTS}
    if counts!=NW_COUNTS: raise RuntimeError('Conteos inesperados después de cargar Northwind.')
    print('Northwind cargada: 830 pedidos y 2155 líneas.')

def load_hr():
    exists=oracle("SELECT COUNT(*) FROM dba_users WHERE username='HR';")
    if exists=='1':
        try: counts={table:int(oracle('SELECT COUNT(*) FROM hr.'+table+';')) for table in HR_COUNTS}
        except RuntimeError: raise RuntimeError('HR ya existe pero está incompleto. Se conserva; revisa su instalación antes de continuar.')
        if counts!=HR_COUNTS: raise RuntimeError('HR ya contiene datos diferentes o está incompleto. Se conserva; no se elimina el esquema.')
        print('HR ya contiene las siete tablas con los conteos esperados; se conserva.'); return
    # La imagen Lite de Oracle Free no incluye el tablespace USERS que usa el esquema HR.
    if oracle("SELECT COUNT(*) FROM dba_tablespaces WHERE tablespace_name='USERS';")=='0':
        oracle("CREATE TABLESPACE users DATAFILE '/opt/oracle/oradata/FREE/FREEPDB1/users01.dbf' SIZE 100M AUTOEXTEND ON NEXT 50M MAXSIZE 2G;")
        print('Tablespace USERS creado en FREEPDB1.')
    password=configuration()['HR_PASSWORD']
    script='''SET ECHO OFF VERIFY OFF DEFINE OFF
CREATE USER hr IDENTIFIED BY "PASSWORD_TOKEN" DEFAULT TABLESPACE users QUOTA UNLIMITED ON users;
GRANT CREATE MATERIALIZED VIEW, CREATE PROCEDURE, CREATE SEQUENCE, CREATE SESSION, CREATE SYNONYM, CREATE TABLE, CREATE TRIGGER, CREATE TYPE, CREATE VIEW TO hr;
CONNECT hr/"PASSWORD_TOKEN"@//localhost:1521/FREEPDB1
WHENEVER SQLERROR EXIT FAILURE
WHENEVER OSERROR EXIT FAILURE
@/datasets/hr_create.sql
@/datasets/hr_populate.sql
@/datasets/hr_code.sql
SELECT COUNT(*) FROM employees;
'''.replace('PASSWORD_TOKEN',password)
    # La contraseña se envía por stdin; no se registra en el comando ni en archivos SQL.
    result=oracle(script)
    print(redact(result))
    counts={table:int(oracle('SELECT COUNT(*) FROM hr.'+table+';')) for table in HR_COUNTS}
    if counts!=HR_COUNTS: raise RuntimeError('Conteos inesperados después de cargar HR.')
    print('HR cargado: 107 empleados y 10 filas de job_history.')

def load_mongo():
    if not (ROOT/'data/procesados/sensores.jsonl').exists(): raise RuntimeError('Falta data/procesados/sensores.jsonl incluido en el proyecto.')
    compose(['exec','-T','mongodb','mongosh','--quiet','--file','/scripts/mongo_verificar.js'])
    cmd='mongoimport --host localhost --username "$MONGO_INITDB_ROOT_USERNAME" --password "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --db bigdata_final --collection sensores_datos --mode upsert --upsertFields sensor_id,timestamp --file /datasets/sensores.jsonl'
    compose(['exec','-T','mongodb','sh','-c',cmd])
    compose(['exec','-T','-e','BIGDATA_EXPECTED_COUNT=12960','mongodb','mongosh','--quiet','--file','/scripts/mongo_verificar.js'])
    print('Importación por clave completada: repetirla conserva una lectura por sensor y timestamp.')

def client(command): return compose(['run','--rm','--no-deps','analisis',*command])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['configurar','validar','iniciar','estado','cargar','construir-cliente','drivers','verificar','integrar','logs','detener'])
    p.add_argument('motor',nargs='?',choices=MOTORS)
    args=p.parse_args()
    if args.action=='configurar': configure(); return
    if args.action=='validar': compose(['config','--quiet']); print('Compose y configuración válidos.'); return
    if args.action=='iniciar': compose(['up','-d','--wait','--wait-timeout','900',*( [args.motor] if args.motor else MOTORS )]); return
    if args.action=='estado': compose(['ps','-a']); return
    if args.action=='cargar':
        if not args.motor: p.error('cargar requiere sqlserver, oracle o mongodb')
        {'sqlserver':load_sql,'oracle':load_hr,'mongodb':load_mongo}[args.motor](); return
    if args.action=='construir-cliente': compose(['build','analisis']); return
    if args.action=='drivers':
        client(['python','-c',"import pyodbc; d=pyodbc.drivers(); print('Drivers ODBC:', d); assert 'ODBC Driver 18 for SQL Server' in d and 'Oracle Instant Client ODBC' in d"]); return
    if args.action=='verificar':
        cmd=['python','src/conexiones.py','verificar']
        if args.motor: cmd+=['--motor',args.motor]
        client(cmd); return
    if args.action=='integrar':
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup=ROOT.parent/'respaldos_bigdata_final'/stamp
        for folder in ['data/procesados','docs','evidencias']:
            shutil.copytree(ROOT/folder,backup/folder)
        print('Respaldo de resultados anteriores:',backup)
        client(['python','run.py','--desde-bd']); return
    if args.action=='logs':
        if not args.motor: p.error('logs requiere sqlserver, oracle o mongodb')
        compose(['logs','--tail','80',args.motor]); return
    if args.action=='detener': compose(['stop',*MOTORS]); return

if __name__=='__main__':
    try: main()
    except (RuntimeError,ValueError,FileNotFoundError) as ex:
        print(redact(str(ex)),file=sys.stderr); raise SystemExit(2)
