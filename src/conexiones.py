"""Verifica conexiones reales, registra evidencia y permite extracción de sólo lectura."""
import os, json, argparse, datetime
from pathlib import Path
import pandas as pd
from origen import registrar_fuente

ROOT=Path(__file__).resolve().parents[1]

def load_env():
    path=ROOT/'config/.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

def connect(motor):
    if motor in ('sqlserver','oracle'):
        key={'sqlserver':'SQLSERVER_ODBC','oracle':'ORACLE_ODBC'}[motor]
        if not os.getenv(key): raise RuntimeError(f'Falta {key} en config/.env')
        import pyodbc
        return pyodbc.connect(os.environ[key],timeout=10)
    if not os.getenv('MONGODB_URI'): raise RuntimeError('Falta MONGODB_URI en config/.env')
    from pymongo import MongoClient
    client=MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=5000)
    client.admin.command('ping'); return client

def verify(motor=None):
    load_env(); results=[]
    for motor in ([motor] if motor else ['sqlserver','oracle','mongodb']):
        result={'motor':motor,'connector':'ODBC' if motor!='mongodb' else 'PyMongo','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified':False}
        try:
            conn=connect(motor)
            if motor=='sqlserver':
                row=conn.cursor().execute('SELECT DB_NAME(), COUNT(*) FROM dbo.Orders').fetchone()
                result.update(database=str(row[0]),orders=int(row[1])); conn.close()
            elif motor=='oracle':
                cursor=conn.cursor()
                schema=cursor.execute("SELECT SYS_CONTEXT('USERENV','CURRENT_SCHEMA') FROM dual").fetchone()[0]
                count=cursor.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
                result.update(schema=str(schema),employees=int(count)); conn.close()
            else:
                db=conn[os.getenv('MONGODB_DATABASE','bigdata_final')]
                result.update(database=db.name,documents=db.sensores_datos.count_documents({})); conn.close()
            count=result.get('orders',result.get('employees',result.get('documents',0)))
            if count<=0: raise RuntimeError('Conexión disponible, pero falta cargar el conjunto de datos requerido.')
            result['verified']=True
        except Exception as ex:
            # No copiar mensajes completos de conexión: podrían contener credenciales.
            result['reason']=str(ex) if isinstance(ex,RuntimeError) else type(ex).__name__+' (ver detalle local sin publicar credenciales)'
        results.append(result)
    output=ROOT/'evidencias/conexiones.json'
    previous={r['motor']:r for r in json.loads(output.read_text())} if output.exists() else {}
    previous.update({r['motor']:r for r in results})
    output.write_text(json.dumps(list(previous.values()),ensure_ascii=False,indent=2))
    lines=['VERIFICACIÓN REAL DE CONEXIONES - '+datetime.datetime.now(datetime.timezone.utc).isoformat()]
    for r in results:
        lines.append(r['motor']+': '+('CONEXIÓN VERIFICADA' if r['verified'] else 'PENDIENTE'))
        lines.append(json.dumps(r,ensure_ascii=False))
    (ROOT/'evidencias/conexiones.txt').write_text(json.dumps(list(previous.values()),ensure_ascii=False,indent=2))
    print('\n'.join(lines))
    return all(r['verified'] for r in results)

def extract(motor):
    load_env(); conn=connect(motor); dest=ROOT/'data/procesados'
    if motor=='sqlserver':
        queries={
          'Orders':'SELECT * FROM dbo.Orders',
          'Order_Details':'SELECT OrderID, ProductID, UnitPrice, Quantity, Discount FROM dbo.[Order Details]',
          'Customers':'SELECT * FROM dbo.Customers',
          'Products':'SELECT * FROM dbo.Products',
          'Categories':'SELECT CategoryID, CategoryName, Description FROM dbo.Categories',
          'Suppliers':'SELECT * FROM dbo.Suppliers',
          'Employees':'SELECT EmployeeID, FirstName, LastName, ReportsTo FROM dbo.Employees'}
        exported=[]
        for name,query in queries.items():
            cur=conn.cursor().execute(query); columns=[x[0] for x in cur.description]
            df=pd.DataFrame.from_records(cur.fetchall(),columns=columns)
            df.to_csv(dest/f'nw_{name}.csv',index=False)
            exported.append(f'nw_{name}.csv')
        conn.close()
        registrar_fuente('sqlserver','base_de_datos',exported)
    elif motor=='oracle':
        tables=['employees','departments','locations','countries','regions','jobs','job_history']
        for table in tables:
            cur=conn.cursor().execute('SELECT * FROM '+table)
            df=pd.DataFrame.from_records(cur.fetchall(),columns=[x[0].lower() for x in cur.description])
            df.to_csv(dest/f'hr_{table}.csv',index=False)
        conn.close()
        registrar_fuente('oracle','base_de_datos',[f'hr_{table}.csv' for table in tables])
    else:
        collection=conn[os.getenv('MONGODB_DATABASE','bigdata_final')].sensores_datos
        df=pd.DataFrame(list(collection.find({},{'_id':0}).sort([('city',1),('station',1),('timestamp',1),('type',1)])))
        if df.empty: raise RuntimeError('La colección sensores_datos está vacía')
        df['timestamp']=pd.to_datetime(df.timestamp,utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        if 'injected_anomaly' not in df: raise RuntimeError('El analizador incluido evalúa sensores sintéticos y requiere injected_anomaly; adapte evaluación para lecturas reales.')
        df.to_csv(dest/'sensores.csv',index=False); conn.close()
        registrar_fuente('mongodb','base_de_datos',['sensores.csv'])
    print('Extracción de sólo lectura completada:',motor)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['verificar','extraer']); parser.add_argument('--motor',choices=['sqlserver','oracle','mongodb']); args=parser.parse_args()
    if args.action=='verificar': raise SystemExit(0 if verify(args.motor) else 2)
    if not args.motor: parser.error('extraer requiere --motor')
    extract(args.motor)
