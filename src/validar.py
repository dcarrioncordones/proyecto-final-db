"""Comprobaciones analíticas y de integridad relevantes para las conclusiones."""
from pathlib import Path
import json
import pandas as pd
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data/procesados'

def main():
    nw=pd.read_csv(DATA/'northwind_analitico.csv'); hr=pd.read_csv(DATA/'hr_analitico.csv'); s=pd.read_csv(DATA/'sensores_analitico.csv'); summary=json.loads((ROOT/'docs/resultados.json').read_text())
    checks={}
    checks['uniones_northwind_sin_multiplicar_lineas']=len(nw)==len(pd.read_csv(DATA/'nw_Order_Details.csv'))
    checks['clave_linea_unica']=not nw.duplicated(['OrderID','ProductID']).any()
    checks['formula_neta']=bool(np.allclose(nw.net,nw.UnitPrice*nw.Quantity*(1-nw.Discount)))
    checks['ventas_reconcilian_mes_cliente_categoria']=all(np.isclose(nw.groupby(col).net.sum().sum(),summary['nw']['net']) for col in ['month','CustomerID','CategoryName','employee'])
    checks['descuentos_validos']=bool(nw.Discount.between(0,1).all())
    checks['empleados_conservados']=len(hr)==len(pd.read_csv(DATA/'hr_employees.csv')) and not hr.employee_id.duplicated().any()
    ids=set(hr.employee_id); checks['supervisores_existen']=set(hr.manager_id.dropna()).issubset(ids)
    def has_cycle(i):
        seen=set(); mapping=hr.set_index('employee_id').manager_id.to_dict()
        while pd.notna(i):
            if i in seen: return True
            seen.add(i); i=mapping.get(i)
        return False
    checks['organigrama_sin_ciclos']=not any(has_cycle(i) for i in ids)
    checks['salarios_positivos']=bool((hr.salary>0).all())
    checks['clave_sensor_tiempo_unica']=not s.duplicated(['sensor_id','timestamp']).any()
    checks['lecturas_sin_nulos_criticos']=not s[['sensor_id','timestamp','type','value','unit']].isna().any().any()
    checks['muestreo_completo']=bool(s.groupby('sensor_id').size().eq(720).all())
    checks['score_mad_finito']=bool(np.isfinite(s.score).all())
    checks['regla_alertas_reproduce']=bool((s.detected==(s.score>3.5)).all())
    tp=int((s.detected&s.injected_anomaly).sum()); fp=int((s.detected&~s.injected_anomaly).sum()); fn=int((~s.detected&s.injected_anomaly).sum())
    checks['matriz_confusion_reconcilia']=all(summary['sensors'][k]==v for k,v in [('tp',tp),('fp',fp),('fn',fn)])
    meta=json.loads((ROOT/'docs/visualizaciones.json').read_text()); checks['treinta_visualizaciones']=len(meta)==30 and len(set(m['id'] for m in meta))==30
    checks['archivos_figuras_validos']=True
    for m in meta:
        with Image.open(ROOT/'figuras'/(m['id']+'.png')) as image: image.verify()
        f=json.loads((ROOT/'dashboard'/(m['id']+'.json')).read_text()); assert len(f['data'])>0
    failed=[k for k,v in checks.items() if not v]
    result={'passed':not failed,'checks':checks,'failed':failed,'scope':'Datos y archivos locales; no valida ejecución SQL/Oracle/MongoDB ni conexiones.'}
    (ROOT/'evidencias/validacion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(f'{sum(checks.values())}/{len(checks)} comprobaciones correctas')
    if failed: raise SystemExit(', '.join(failed))

if __name__=='__main__': main()
