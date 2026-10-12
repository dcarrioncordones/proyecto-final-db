"""Extrae INSERT de muestras oficiales sin ejecutar SQL; genera sensores reproducibles."""
from pathlib import Path
import re, json, hashlib
import pandas as pd
import numpy as np
from origen import registrar_fuente

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/procesados'
SCHEMA = {
 'Customers':['CustomerID','CompanyName','ContactName','ContactTitle','Address','City','Region','PostalCode','Country','Phone','Fax'],
 'Order Details':['OrderID','ProductID','UnitPrice','Quantity','Discount'],
 'regions':['region_id','region_name'],
 'countries':['country_id','country_name','region_id'],
 'locations':['location_id','street_address','postal_code','city','state_province','country_id'],
 'departments':['department_id','department_name','manager_id','location_id'],
 'jobs':['job_id','job_title','min_salary','max_salary'],
 'employees':['employee_id','first_name','last_name','email','phone_number','hire_date','job_id','salary','commission_pct','manager_id','department_id'],
 'job_history':['employee_id','start_date','end_date','job_id','department_id']}

def split_values(s):
    tokens=[]; start=0; depth=0; quote=False; i=0
    while i<len(s):
        c=s[i]
        if c=="'":
            if quote and i+1<len(s) and s[i+1]=="'": i+=2; continue
            quote=not quote
        elif not quote:
            if c=='(': depth+=1
            elif c==')': depth-=1
            elif c==',' and depth==0: tokens.append(s[start:i].strip()); start=i+1
        i+=1
    tokens.append(s[start:].strip())
    return tokens

def literal(v):
    v=v.strip()
    if v.upper()=='NULL': return None
    if v.upper().startswith('TO_DATE'):
        d=re.search(r"'([^']+)'",v)[1]
        return pd.to_datetime(d,format='%d-%m-%Y').isoformat()[:10]
    if v.startswith("N'"): v=v[1:]
    if v.startswith("'"): return v[1:-1].replace("''", "'")
    if v.lower().startswith('0x'): return None # No se usan imágenes binarias
    try: return float(v) if '.' in v else int(v)
    except ValueError: raise ValueError('Literal no soportado: '+v[:80])

def parse_file(path, oracle=False):
    txt=path.read_text(encoding='utf-8-sig')
    pattern=r'INSERT\s+(?:INTO\s+)?(?:"([^"]+)"|(\w+))\s*(\([^)]*\))?\s*VALUES\s*\('
    rows={}; columns={}
    for m in re.finditer(pattern,txt,re.I):
        name=m[1] or m[2]
        if oracle and name not in SCHEMA: continue
        pos=m.end(); start=pos; depth=1; quote=False
        while depth and pos<len(txt):
            c=txt[pos]
            if c=="'":
                if quote and pos+1<len(txt) and txt[pos+1]=="'": pos+=2; continue
                quote=not quote
            elif not quote:
                depth+= (c=='(')-(c==')')
            pos+=1
        vals=[literal(v) for v in split_values(txt[start:pos-1])]
        col=[x.strip().strip('"') for x in m[3][1:-1].split(',')] if m[3] else columns.get(name,SCHEMA.get(name))
        if col is None: continue
        assert len(vals)==len(col),(name,len(vals),len(col))
        columns[name]=col; rows.setdefault(name,[]).append(vals)
    frames={k:pd.DataFrame(v,columns=columns[k]) for k,v in rows.items()}
    for k,v in frames.items(): v.to_csv(OUT/(('hr_' if oracle else 'nw_')+k.replace(' ','_')+'.csv'),index=False)
    return frames

def sensors():
    rng=np.random.default_rng(5122026)
    cities={'Santo Domingo':(18.4861,-69.9312,28), 'Santiago':(19.4517,-70.697,26), 'Punta Cana':(18.5601,-68.3725,27)}
    times=pd.date_range('2026-09-01',periods=30*24,freq='h',tz='America/Santo_Domingo')
    rows=[]
    for city,(lat,lon,base) in cities.items():
        prefix={'Santo Domingo':'SDQ','Santiago':'STI','Punta Cana':'PUJ'}[city]
        for station in range(2):
            for t in times:
                daily=np.sin(2*np.pi*(t.hour-9)/24)
                weather=rng.normal(0,.8)
                temp=base+3*daily+station*.3+weather
                humidity=np.clip(72-2.2*(temp-base)+rng.normal(0,4),20,100)
                co2=430+45*(8<=t.hour<=18)+rng.normal(0,15)
                for typ,val,unit in [('temperatura',temp,'°C'),('humedad',humidity,'%'),('co2',co2,'ppm')]:
                    injected=bool(rng.random()<.008)
                    if injected: val+= {'temperatura':15,'humedad':-35,'co2':300}[typ]
                    rows.append(dict(timestamp=t.isoformat(),city=city,station=f'{prefix}-{station+1}',sensor_id=f'{prefix}-{station+1}-{typ}',type=typ,value=round(float(val),3),unit=unit,latitude=lat+station*.015,longitude=lon+station*.015,injected_anomaly=injected))
    df=pd.DataFrame(rows); df.to_csv(OUT/'sensores.csv',index=False)
    with (OUT/'sensores.jsonl').open('w') as f:
        for row in rows:
            row['timestamp']={'$date':row['timestamp']}; f.write(json.dumps(row,ensure_ascii=False)+'\n')
    return df

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    nw=parse_file(ROOT/'data/original/instnwnd.sql')
    hr=parse_file(ROOT/'data/original/hr_populate.sql',True)
    s=sensors()
    counts={**{'nw_'+k:len(v) for k,v in nw.items()},**{'hr_'+k:len(v) for k,v in hr.items()},'sensores':len(s)}
    assert counts['nw_Orders']==830 and counts['nw_Order Details']==2155 and counts['nw_Customers']==91
    assert counts['hr_employees']==107 and counts['hr_job_history']==10
    assert len(s)==12960 and not s.duplicated(['sensor_id','timestamp']).any()
    metadata={'mode':'muestras_oficiales_sin_conexion_a_motor; sensores_sinteticos','seed':5122026,'counts':counts,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/original').glob('*.sql')}}
    (OUT/'proveniencia.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False))
    registrar_fuente('sqlserver','muestra',[p.name for p in OUT.glob('nw_*.csv')])
    registrar_fuente('oracle','muestra',[p.name for p in OUT.glob('hr_*.csv') if p.name!='hr_analitico.csv'])
    registrar_fuente('mongodb','muestra',['sensores.csv'])
    print(json.dumps(counts,ensure_ascii=False))

if __name__=='__main__': main()
