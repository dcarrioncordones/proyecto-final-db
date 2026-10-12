"""Dashboard HTML local; todos los recursos necesarios se distribuyen en la carpeta."""
from pathlib import Path
import json, html
import pandas as pd
from plotly.offline import get_plotlyjs
from origen import estados_fuentes

ROOT=Path(__file__).resolve().parents[1]

def main():
    folder=ROOT/'dashboard'
    (folder/'plotly.min.js').write_text(get_plotlyjs())
    meta=json.loads((ROOT/'docs/visualizaciones.json').read_text())
    figures={m['id']:json.loads((folder/(m['id']+'.json')).read_text()) for m in meta}
    nw=pd.read_csv(ROOT/'data/procesados/northwind_analitico.csv')
    hr=pd.read_csv(ROOT/'data/procesados/hr_analitico.csv')
    s=pd.read_csv(ROOT/'data/procesados/sensores_analitico.csv')
    sources=estados_fuentes()
    live_count=sum(v.get('mode')=='base_de_datos' for v in sources.values())
    aviso=('Análisis calculado sobre datos extraídos de SQL Server, Oracle y MongoDB. Las lecturas de sensores siguen siendo una simulación; el dashboard muestra una exportación, no consulta los gestores en vivo.' if live_count==3 else f'Análisis reproducible: {live_count} de 3 fuentes tienen extracción desde un gestor registrada y verificable. Las otras fuentes usan archivos de muestra. Revisa evidencias/conexiones.json para las pruebas de acceso.')
    payload={'meta':meta,'figures':figures,'sources':sources,'summary':json.loads((ROOT/'docs/resultados.json').read_text()),
      'sales':nw[['Country','month','net']].to_dict('records'),
      'employees':hr[['department_name','salary']].to_dict('records'),
      'sensors':s[['sensor_id','timestamp','value','unit','detected']].to_dict('records')}
    template=(ROOT/'src/dashboard_template.html').read_text()
    encoded=json.dumps(payload,ensure_ascii=False).replace('</','<\\/')
    (folder/'index.html').write_text(template.replace('__DATA__',encoded).replace('__ORIGEN_AVISO__',html.escape(aviso)))
    print('Dashboard listo:',(folder/'index.html').relative_to(ROOT))

if __name__=='__main__': main()
