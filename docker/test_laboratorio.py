"""Pruebas sin Docker ni conexiones: protección de datos y registro de procedencia."""
from pathlib import Path
import contextlib, importlib.util, io, os, re, tempfile, unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result
lab=module('lab',ROOT/'docker/lab.py')
origen=module('origen',ROOT/'src/origen.py')
cliente=module('cliente',ROOT/'docker/cliente.py')

class Laboratorio(unittest.TestCase):
    def test_configuracion_preserva_credenciales_y_permisos(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(lab,'ENVFILE',Path(tmp)/'.env'):
            with contextlib.redirect_stdout(io.StringIO()): lab.configure()
            first=lab.ENVFILE.read_bytes(); config=lab.configuration()
            self.assertEqual(len({config[k] for k in config if k.endswith('PASSWORD')}),4)
            self.assertEqual(lab.ENVFILE.stat().st_mode & 0o777,0o600)
            with contextlib.redirect_stdout(io.StringIO()): lab.configure()
            self.assertEqual(first,lab.ENVFILE.read_bytes())
            self.assertEqual(lab.redact('Error '+config['SQL_PASSWORD']),'Error [oculto]')

    def test_northwind_incompleta_no_se_reinstala(self):
        def query(q,database='master'):
            if database=='master': return '1'
            if 'sys.tables' in q: return '7'
            table=re.search(r'dbo\.\[([^]]+)\]',q).group(1)
            return str(1 if table=='Order Details' else lab.NW_COUNTS[table])
        with patch.object(lab,'sql',side_effect=query), patch.object(lab,'compose') as compose:
            with self.assertRaisesRegex(RuntimeError,'Se conserva'): lab.load_sql()
            compose.assert_not_called()

    def test_northwind_cargada_no_se_modifica(self):
        def query(q,database='master'):
            if database=='master': return '1'
            if 'sys.tables' in q: return '7'
            return str(lab.NW_COUNTS[re.search(r'dbo\.\[([^]]+)\]',q).group(1)])
        with patch.object(lab,'sql',side_effect=query), patch.object(lab,'compose') as compose:
            with contextlib.redirect_stdout(io.StringIO()): lab.load_sql()
            compose.assert_not_called()

    def test_hr_incompleto_no_se_reinstala(self):
        def query(q):
            if 'dba_users' in q: return '1'
            table=re.search(r'hr\.([a-z_]+)',q).group(1)
            return str(0 if table=='job_history' else lab.HR_COUNTS[table])
        with patch.object(lab,'oracle',side_effect=query) as oracle:
            with self.assertRaisesRegex(RuntimeError,'Se conserva'): lab.load_hr()
            self.assertFalse(any('CREATE USER' in call.args[0] for call in oracle.call_args_list))

    def test_cliente_usa_red_interna_y_escapa_credenciales(self):
        base={'SQL_PASSWORD':'Sql_abc;}123','HR_PASSWORD':'Hr_ab}c123','MONGO_PASSWORD':'Mon_abc@123'}
        env=cliente.environment(base)
        self.assertIn('SERVER=sqlserver,1433;',env['SQLSERVER_ODBC'])
        self.assertIn('PWD={Sql_abc;}}123}',env['SQLSERVER_ODBC'])
        self.assertIn('DBQ=oracle:1521/FREEPDB1;',env['ORACLE_ODBC'])
        self.assertIn('Mon_abc%40123@mongodb:27017',env['MONGODB_URI'])
        self.assertNotIn('SQLSERVER_ODBC',base)

    def test_marcadores_no_se_usan_como_credenciales(self):
        with self.assertRaisesRegex(RuntimeError,'SQL_PASSWORD'):
            cliente.environment({'SQL_PASSWORD':'CAMBIAR_SQL'})

    def test_modificar_csv_invalida_procedencia_de_extraccion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); data=root/'data/procesados'; data.mkdir(parents=True)
            (data/'nw_Orders.csv').write_text('OrderID\n1\n')
            with patch.object(origen,'ROOT',root), patch.object(origen,'PATH',data/'proveniencia_fuentes.json'):
                origen.registrar_fuente('sqlserver','base_de_datos',['nw_Orders.csv'])
                self.assertEqual(origen.estados_fuentes()['sqlserver']['mode'],'base_de_datos')
                (data/'nw_Orders.csv').write_text('OrderID\n2\n')
                self.assertEqual(origen.estados_fuentes()['sqlserver']['mode'],'archivos_modificados')
                origen.registrar_fuente('sqlserver','muestra',['nw_Orders.csv'])
                self.assertEqual(origen.estados_fuentes()['sqlserver']['mode'],'muestra')

if __name__=='__main__': unittest.main()
