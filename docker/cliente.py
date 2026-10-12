"""Construye conexiones locales dentro de Compose sin escribir contraseñas en archivos."""
import os, sys
from urllib.parse import quote

def odbc(value): return '{'+value.replace('}','}}')+'}'

def environment(base):
    env=base.copy()
    for key in ['SQL_PASSWORD','HR_PASSWORD','MONGO_PASSWORD']:
        if not env.get(key) or env[key].startswith('CAMBIAR'): raise RuntimeError('Configura docker/.env: '+key)
    # Servidor del laboratorio en red Docker privada con certificado autofirmado.
    # Se conserva cifrado; la excepción de validación está limitada a este laboratorio.
    env['SQLSERVER_ODBC']='DRIVER={ODBC Driver 18 for SQL Server};SERVER='+env.get('SQLSERVER_HOST','sqlserver,1433')+';DATABASE=Northwind;UID=sa;PWD='+odbc(env['SQL_PASSWORD'])+';Encrypt=yes;TrustServerCertificate=yes'
    # El driver ODBC de Oracle no interpreta {…}: la contraseña va sin llaves (lab.py sólo admite letras, números, _ y -).
    env['ORACLE_ODBC']='DRIVER={Oracle Instant Client ODBC};DBQ='+env.get('ORACLE_SERVICE','oracle:1521/FREEPDB1')+';UID=hr;PWD='+env['HR_PASSWORD']
    env['MONGODB_URI']='mongodb://bigdata_admin:'+quote(env['MONGO_PASSWORD'],safe='')+'@'+env.get('MONGODB_HOST','mongodb:27017')+'/?authSource=admin'
    env['MONGODB_DATABASE']='bigdata_final'
    return env

if __name__=='__main__':
    try:
        env=environment(os.environ)
        cmd=sys.argv[1:] or ['python','src/conexiones.py','verificar']
        os.execvpe(cmd[0],cmd,env)
    except RuntimeError as ex:
        print(str(ex),file=sys.stderr); raise SystemExit(2)
