"""Crea un notebook portátil; --ejecutar verifica todas las celdas con el Python actual."""
from pathlib import Path
import argparse, os, sys
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--ejecutar',action='store_true'); args=parser.parse_args()
    nb=nbf.v4.new_notebook()
    nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
    nb.cells=[nbf.v4.new_markdown_cell('# Trabajo final de Big Data\n\nDan Carrión · Matrícula 1131022 · INTEC\n\n30 visualizaciones con Northwind, HR y sensores. **Origen:** scripts oficiales extraídos sin conexión a motores; sensores sintéticos, semilla 5122026. Las evidencias de conexión deben completarse con `src/conexiones.py`. La ejecución siguiente reconstruye datos y gráficos locales; no escribe en bases de datos.'),
      nbf.v4.new_code_cell("from pathlib import Path\nimport sys, subprocess, json\nfrom IPython.display import display, Image\nroot = Path.cwd()\nif (root / 'proyecto_final').is_dir():\n    root = root / 'proyecto_final'\nassert (root / 'src/analisis.py').exists(), 'Abre Jupyter desde la carpeta del proyecto'\nprint('Proyecto:', root.name)"),
      nbf.v4.new_markdown_cell('## Preparación y análisis\n\nLos scripts leen los originales, generan la simulación, calculan las tablas analíticas y crean figuras sobre esos mismos cálculos.'),
      nbf.v4.new_code_cell("# Si los CSV vienen de los gestores (run.py --desde-bd), no se reconstruyen las muestras.\nfuentes = root / 'data/procesados/proveniencia_fuentes.json'\nextraido = fuentes.exists() and any(r.get('mode') == 'base_de_datos' for r in json.loads(fuentes.read_text()).values())\nscripts = ['analisis.py', 'dashboard.py', 'validar.py'] if extraido else ['preparar_datos.py', 'analisis.py', 'dashboard.py', 'validar.py']\nfor script in scripts:\n    result = subprocess.run([sys.executable, str(root / 'src' / script)], cwd=root, capture_output=True, text=True, check=True)\n    print(script)\n    print(result.stdout)\n    if result.stderr:\n        print(result.stderr)"),
      nbf.v4.new_markdown_cell('## Resultados comprobables\n\nLos indicadores provienen de cálculos sobre las muestras. La evaluación de anomalías usa el mismo mes para referencia y revisión: es retrospectiva.'),
      nbf.v4.new_code_cell("results = json.loads((root / 'docs/resultados.json').read_text())\nprint(json.dumps(results, indent=2, ensure_ascii=False))\nchecks = json.loads((root / 'evidencias/validacion.json').read_text())\nassert checks['passed']\nprint('Comprobaciones correctas:', len(checks['checks']))")]
    for prefix,label in [('N','SQL Server / Northwind'),('H','Oracle / HR'),('S','MongoDB / sensores sintéticos')]:
        nb.cells.append(nbf.v4.new_markdown_cell('## '+label+'\n\nCada figura se acompaña de método, resultado y límite. Los scripts de consulta están en `sql/` y `mongo/`.'))
        nb.cells.append(nbf.v4.new_code_cell("meta = json.loads((root / 'docs/visualizaciones.json').read_text())\nfor item in [m for m in meta if m['id'].startswith('"+prefix+"')]:\n    print(item['id'] + ' · ' + item['title'])\n    print('Método:', item['method'])\n    display(Image(filename=str(root / 'figuras' / (item['id'] + '.png')), width=900))\n    print('Resultado:', item['insight'])\n    print('Decisión:', item['decision'])\n    print('Límite:', item['limit'])\n    print()"))
    nb.cells.append(nbf.v4.new_markdown_cell('## Dashboard y conexiones\n\nAbre `dashboard/index.html` en un navegador. N01 permite filtrar país, H01 departamento y S06/S10 sensor. S10 reproduce historia; no consulta un flujo real.\n\nPara comprobar los tres gestores, completa `config/.env` y ejecuta `python src/conexiones.py verificar`. Esa operación sólo se realiza al disponer del acceso; no se inventan capturas exitosas.\n\nEl informe final está en `informe/salida/`. La guía de instalación está en `README.md` y `COMO_CORRER.md`.'))
    path=ROOT/'Trabajo_final_Big_Data.ipynb'
    nbf.write(nb,path)
    if args.ejecutar:
        from nbclient import NotebookClient
        from jupyter_client import KernelManager
        runtime=ROOT/'.jupyter'; runtime.mkdir(exist_ok=True); os.environ['JUPYTER_RUNTIME_DIR']=str(runtime); os.environ['IPYTHONDIR']=str(runtime/'ipython')
        km=KernelManager(kernel_name='python3'); km.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
        client=NotebookClient(nb,km=km,timeout=180,resources={'metadata':{'path':str(ROOT)}})
        client.execute(); nbf.write(nb,path)
        assert all(not any(o.output_type=='error' for o in c.get('outputs',[])) for c in nb.cells)
        print('Notebook ejecutado sin errores:',path)
    else: print('Notebook creado:',path)

if __name__=='__main__': main()
