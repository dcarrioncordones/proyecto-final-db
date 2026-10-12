"""30 figuras estáticas y 30 figuras Plotly, con resultados calculados y trazabilidad."""
from pathlib import Path
import os, json, calendar, warnings
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'.mplcache'))
import matplotlib
matplotlib.use('Agg')
# Aviso cosmético de una figura sin ejes (red de sensores); no afecta el resultado.
warnings.filterwarnings('ignore', message='constrained_layout not applied')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, PathPatch
from matplotlib.path import Path as MPath
from matplotlib.colors import Normalize
import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data/procesados'
COLORS=['#0072B2','#E69F00','#009E73','#CC79A7','#D55E00','#56B4E9','#8A8A8A','#332288','#44AA99']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#334155','axes.edgecolor':'#CBD5E1','figure.facecolor':'white','axes.prop_cycle':matplotlib.cycler(color=COLORS)})
META=[]; FIGS={}

def read(name): return pd.read_csv(DATA/(name+'.csv'))
def cash(v): return f'{v:,.2f}'
def canvas(): return plt.subplots(figsize=(10,5.6),layout='constrained')
def register(id,title,fig,pfig,method,insight,decision,limit,code):
    fig.savefig(ROOT/'figuras'/f'{id}.png',dpi=165,bbox_inches='tight'); plt.close(fig)
    pfig.update_layout(template='plotly_white',title=title,font=dict(family='Arial',size=12),height=540,margin=dict(l=65,r=30,t=75,b=75),colorway=COLORS)
    pfig.write_json(ROOT/'dashboard'/f'{id}.json')
    META.append(dict(id=id,title=title,method=method,insight=insight,decision=decision,limit=limit,code=code))
    FIGS[id]=pfig

def heat(ax,df,label,fmt=None):
    im=ax.imshow(df.values,aspect='auto',cmap='YlGnBu'); ax.set_xticks(range(len(df.columns)),df.columns,rotation=45,ha='right'); ax.set_yticks(range(len(df)),df.index)
    plt.colorbar(im,ax=ax,label=label,shrink=.85)
    if fmt:
        mid=np.nanmax(df.values)/2
        for i in range(len(df)):
            for j in range(len(df.columns)):
                ax.text(j,i,format(df.iloc[i,j],fmt),ha='center',va='center',fontsize=8,color='white' if df.iloc[i,j]>mid else '#334155')

def load():
    orders=read('nw_Orders'); orders['OrderDate']=pd.to_datetime(orders.OrderDate,format='mixed')
    details=read('nw_Order_Details'); products=read('nw_Products'); customers=read('nw_Customers'); categories=read('nw_Categories'); employees=read('nw_Employees'); suppliers=read('nw_Suppliers')
    assert details.merge(orders,on='OrderID',validate='many_to_one').shape[0]==len(details)
    nw=details.merge(orders,on='OrderID',validate='many_to_one').merge(products[['ProductID','ProductName','CategoryID']],on='ProductID',validate='many_to_one').merge(categories[['CategoryID','CategoryName']],on='CategoryID',validate='many_to_one').merge(customers[['CustomerID','CompanyName','Country']],on='CustomerID',validate='many_to_one').merge(employees[['EmployeeID','FirstName','LastName']],on='EmployeeID',validate='many_to_one')
    nw['net']=nw.UnitPrice*nw.Quantity*(1-nw.Discount); nw['gross']=nw.UnitPrice*nw.Quantity; nw['month']=nw.OrderDate.dt.to_period('M').astype(str); nw['employee']=nw.FirstName+' '+nw.LastName
    hr=read('hr_employees'); hr['hire_date']=pd.to_datetime(hr.hire_date)
    hr=hr.merge(read('hr_departments')[['department_id','department_name','location_id']],on='department_id',how='left',validate='many_to_one').merge(read('hr_locations')[['location_id','city','country_id']],on='location_id',how='left',validate='many_to_one').merge(read('hr_countries'),on='country_id',how='left',validate='many_to_one').merge(read('hr_regions'),on='region_id',how='left',validate='many_to_one').merge(read('hr_jobs'),on='job_id',validate='many_to_one')
    hr['department_name']=hr.department_name.fillna('Sin departamento'); hr['region_name']=hr.region_name.fillna('Sin región'); hr['city']=hr.city.fillna('Sin ubicación')
    hr['tenure']=(pd.Timestamp('2026-10-08')-hr.hire_date).dt.days/365.25
    hr['level']=pd.cut(hr.tenure,[0,9,12,100],labels=['Menos de 9 años','9 a menos de 12','12 años o más'],right=False)
    s=read('sensores'); s['timestamp']=pd.to_datetime(s.timestamp,utc=True).dt.tz_convert('America/Santo_Domingo'); s['hour']=s.timestamp.dt.hour; s['date']=s.timestamp.dt.date
    g=s.groupby(['sensor_id','hour']).value
    s['baseline']=g.transform('median'); s['absdev']=(s.value-s.baseline).abs(); s['mad']=s.groupby(['sensor_id','hour']).absdev.transform('median')
    s['score']=s.absdev/(1.4826*s.mad.replace(0,np.nan)); s['detected']=s.score>3.5
    assert len(nw)==2155 and len(hr)==107 and s.score.notna().all()
    nw.to_csv(DATA/'northwind_analitico.csv',index=False); hr.to_csv(DATA/'hr_analitico.csv',index=False); s.to_csv(DATA/'sensores_analitico.csv',index=False)
    return orders,nw,products,customers,suppliers,hr,s

def northwind(orders,d,products,customers,suppliers):
    monthly=d.groupby('month').net.sum(); roll=monthly.rolling(3,min_periods=3).mean()
    fig,ax=canvas(); ax.plot(monthly.index,monthly.values,'o-',label='Venta neta'); ax.plot(roll.index,roll.values,label='Media móvil de 3 meses'); ax.set_xticks(range(0,len(monthly),2),monthly.index[::2],rotation=45,ha='right'); ax.set_ylabel('Importe neto (unidad monetaria de muestra)'); ax.legend(); ax.set_title('Ventas mensuales y media móvil')
    p=go.Figure([go.Scatter(x=monthly.index,y=monthly,name='Venta neta'),go.Scatter(x=roll.index,y=roll,name='Media móvil 3 meses')]); p.update_yaxes(title='Importe neto'); p.update_xaxes(title='Mes de pedido')
    peak=monthly.idxmax()
    register('N01','Ventas mensuales y tendencia',fig,p,'Se suma precio de línea × cantidad × (1 - descuento) por mes. La tendencia promedia tres observaciones mensuales consecutivas; conserva los períodos parciales y requiere tres observaciones.',f'El total neto es {cash(d.net.sum())}; el máximo mensual corresponde a {peak}, con {cash(monthly.max())}.','Ajustar inventario y capacidad para meses de mayor demanda, confirmando el patrón con un período más amplio.','Julio de 1996 y mayo de 1998 son períodos parciales. Las ventas no incluyen flete, impuestos ni costos. No se interpreta el último mes como caída económica.',"monthly = d.groupby('month').net.sum()\ntrend = monthly.rolling(3, min_periods=3).mean()")
    topcountries=d.groupby('Country').net.sum().nlargest(8).index; mat=d[d.Country.isin(topcountries)].pivot_table(index='CategoryName',columns='Country',values='net',aggfunc='sum',fill_value=0)/1000
    fig,ax=canvas(); heat(ax,mat,'Venta neta en miles','.1f'); ax.set_title('Categoría y país del cliente'); p=px.imshow(mat,text_auto='.1f',labels=dict(color='Miles de importe neto',x='País',y='Categoría'),aspect='auto')
    cat=d.groupby('CategoryName').net.sum().sort_values(ascending=False)
    register('N02','Mapa de calor: categoría y país',fig,p,'Se cruzan categorías con los ocho países con mayor venta neta. El color representa importe en miles; país es el domicilio del cliente.',f'{cat.index[0]} lidera por categoría con {cash(cat.iloc[0])}, equivalente al {100*cat.iloc[0]/d.net.sum():.1f}% del total.','Adaptar el portafolio a las combinaciones de mercado y categoría con mayor facturación.','No se incluye el resto de países en la matriz. Una celda elevada puede resultar de pocos pedidos grandes; no equivale a mayor penetración de mercado.',"d.pivot_table(index='CategoryName', columns='Country',\n              values='net', aggfunc='sum', fill_value=0)")
    clients=d.groupby('CompanyName').net.sum().nlargest(10).sort_values(); fig,ax=canvas(); ax.barh(clients.index,clients.values); ax.set_xlabel('Venta neta'); ax.set_title('Top 10 clientes por compras'); p=px.bar(x=clients.values,y=clients.index,orientation='h',labels={'x':'Venta neta','y':'Cliente'})
    register('N03','Top 10 clientes por volumen monetario',fig,p,'Se agrupan las líneas por cliente y se ordena la suma de venta neta. Volumen se define aquí como importe, no unidades.',f'{clients.index[-1]} encabeza las compras con {cash(clients.iloc[-1])}. Los diez primeros concentran {100*clients.sum()/d.net.sum():.1f}% de las ventas.','Diseñar seguimiento de cuentas clave y evaluar riesgo de concentración.','El ranking histórico no mide fidelidad ni valor futuro. Dos clientes del catálogo no tienen pedidos y aportan cero al análisis comercial.',"clients = d.groupby('CompanyName').net.sum().nlargest(10)")
    q=d.assign(quarter=d.OrderDate.dt.to_period('Q').astype(str)).groupby('quarter').net.sum(); fig,ax=canvas(); ax.plot(q.index,q.values,'o-'); ax.set_ylabel('Venta neta'); ax.set_title('Evolución trimestral'); ax.tick_params(axis='x',rotation=35); p=px.line(x=q.index,y=q.values,markers=True,labels={'x':'Trimestre','y':'Venta neta'})
    register('N04','Evolución de ventas trimestrales',fig,p,'Cada pedido se asigna al trimestre de OrderDate; la suma se calcula a partir de líneas, sin multiplicar pedidos por uniones adicionales.',f'El trimestre de mayor importe es {q.idxmax()}, con {cash(q.max())}.','Comparar los trimestres completos de 1997 antes de utilizar la serie para presupuestar.','1996-Q3 y 1998-Q2 tienen cobertura parcial. Una diferencia de duración impide compararlos directamente con trimestres completos.',"q = d.assign(quarter=d.OrderDate.dt.to_period('Q').astype(str))\nq = q.groupby('quarter').net.sum()")
    # Treemap estático: bandas de categoría y rectángulos de producto, áreas proporcionales.
    prod=d.groupby(['CategoryName','ProductName'],as_index=False).net.sum(); fig,ax=canvas(); y=0; total=prod.net.sum()
    for i,(catname,g) in enumerate(prod.groupby('CategoryName')):
        h=g.net.sum()/total; x=0
        for _,r in g.sort_values('net',ascending=False).iterrows():
            w=r.net/g.net.sum(); ax.add_patch(Rectangle((x,y),w,h,facecolor=COLORS[i],edgecolor='white',lw=1));
            if w>.095 and h>.065: ax.text(x+w/2,y+h/2,r.ProductName[:20],ha='center',va='center',fontsize=7,clip_on=True,color='white' if i in [0,2,4,7] else '#111827')
            x+=w
        ax.text(1.01,y+h/2,catname,fontsize=9,va='center'); y+=h
    ax.set_xlim(0,1.22); ax.set_ylim(0,1); ax.axis('off'); ax.set_title('Área = venta neta de cada producto'); p=px.treemap(prod,path=['CategoryName','ProductName'],values='net',color='CategoryName',color_discrete_sequence=COLORS)
    leader=prod.loc[prod.net.idxmax()]
    register('N05','Treemap de productos por categoría',fig,p,'Cada área es proporcional a venta neta. Los productos se anidan en sus categorías; el dashboard permite abrir cada categoría.',f'{leader.ProductName} aporta {cash(leader.net)}, el mayor importe de un producto de la muestra.','Priorizar disponibilidad de productos de gran contribución y contrastar su margen cuando se disponga de costos.','La muestra no contiene costo de compra ni utilidad. Este gráfico mide contribución a ingresos y no rentabilidad.',"prod = d.groupby(['CategoryName','ProductName'], as_index=False).net.sum()\npx.treemap(prod, path=['CategoryName','ProductName'], values='net')")
    corr=d.Discount.corr(d.Quantity); fig,ax=canvas(); ax.scatter(d.Discount*100,d.Quantity,alpha=.18,s=20); ax.set_xlabel('Descuento de línea (%)'); ax.set_ylabel('Unidades por línea'); ax.set_title('Descuentos y cantidades'); p=px.scatter(d,x='Discount',y='Quantity',color='CategoryName',opacity=.35,labels={'Discount':'Descuento (fracción)','Quantity':'Unidades'})
    register('N06','Dispersión: descuento y cantidad',fig,p,'Cada punto corresponde a una línea. Se calcula Pearson entre descuento fraccional y cantidad; los descuentos repetidos producen columnas de puntos.',f'La correlación observada es r = {corr:.3f} en {len(d):,} líneas.','Explorar descuentos por producto y cliente antes de evaluar una política promocional.','Una asociación no prueba que el descuento cause más ventas. Mezcla categorías, productos y condiciones de compra.',"r = d.Discount.corr(d.Quantity)\npx.scatter(d, x='Discount', y='Quantity', color='CategoryName')")
    c=customers.groupby('Country').size().sort_values(ascending=False); shown=pd.concat([c.head(7),pd.Series({'Otros':c.iloc[7:].sum()})]); fig,ax=canvas(); ax.pie(shown,labels=shown.index,autopct='%1.0f%%',colors=COLORS); ax.set_title('Clientes del catálogo por país'); p=px.pie(names=shown.index,values=shown.values,color_discrete_sequence=COLORS)
    register('N07','Distribución de países de clientes',fig,p,'Se cuenta cada CustomerID del catálogo una vez. Los siete países con más clientes se muestran por separado y los demás se agrupan en Otros.',f'Hay {len(customers)} clientes de {len(c)} países. {c.index[0]} tiene {c.iloc[0]} clientes ({100*c.iloc[0]/len(customers):.1f}%).','Usar la distribución para contextualizar la cobertura comercial junto con importes de venta.','Representa clientes registrados; no población, participación de mercado ni clientes activos. Otros combina países distintos.',"c = customers.groupby('Country').size()")
    ps=products.merge(suppliers[['SupplierID','CompanyName']],on='SupplierID',validate='many_to_one'); leaders=ps.groupby('CompanyName').size().nlargest(8).index; sub=ps[ps.CompanyName.isin(leaders)]
    fig,ax=canvas(); arr=[sub[sub.CompanyName==n].UnitPrice for n in leaders]; ax.boxplot(arr,orientation='horizontal',tick_labels=[n[:29] for n in leaders],showmeans=True); ax.set_xlabel('Precio de catálogo'); ax.set_title('Precios de los 8 proveedores con más productos'); p=px.box(sub,x='UnitPrice',y='CompanyName',points='all',labels={'UnitPrice':'Precio de catálogo','CompanyName':'Proveedor'})
    register('N08','Box plot de precios por proveedor',fig,p,'Se usa Products.UnitPrice, distinto del precio histórico de cada venta. Se eligen ocho proveedores por cantidad de productos y se muestran mediana, cuartiles y puntos extremos.',f'El catálogo contiene {len(products)} productos y {len(suppliers)} proveedores; el precio mediano es {cash(products.UnitPrice.median())}.','Revisar proveedores con dispersión elevada para entender mezcla y posicionamiento del portafolio.','Las muestras por proveedor son pequeñas y las categorías difieren. Un precio extremo no es automáticamente un error.',"sub = products.merge(suppliers, on='SupplierID')\npx.box(sub, x='UnitPrice', y='CompanyName', points='all')")
    emp=d.pivot_table(index='month',columns='employee',values='net',aggfunc='sum',fill_value=0).cumsum(); fig,ax=canvas(); ax.stackplot(np.arange(len(emp)),emp.T.values,labels=emp.columns); ax.set_xticks(range(0,len(emp),3),emp.index[::3],rotation=45,ha='right'); ax.set_ylabel('Venta neta acumulada'); ax.legend(loc='upper left',fontsize=8,ncol=2); ax.set_title('Contribución acumulada por empleado'); p=px.area(emp.reset_index().melt('month',var_name='Empleado',value_name='Acumulado'),x='month',y='Acumulado',color='Empleado',labels={'month':'Mes'})
    ranking=d.groupby('employee').net.sum().sort_values(ascending=False)
    register('N09','Áreas: ventas acumuladas por empleado',fig,p,'Se suman las ventas por empleado y mes, se completan celdas ausentes con cero y se aplica acumulado temporal. Las áreas se apilan; el valor individual es el espesor de cada banda.',f'{ranking.index[0]} registra {cash(ranking.iloc[0])}, equivalente al {100*ranking.iloc[0]/d.net.sum():.1f}% del importe neto.','Combinar la contribución con número de pedidos, cartera asignada y metas para evaluar desempeño.','La posición superior de una banda no representa su valor individual. Las ventas no miden productividad ajustada por oportunidades.',"emp = d.pivot_table(index='month', columns='employee',\n values='net', aggfunc='sum', fill_value=0).cumsum()")
    orders=orders.copy(); orders['weekday']=orders.OrderDate.dt.dayofweek; orders['yearmonth']=orders.OrderDate.dt.to_period('M').astype(str)
    om=orders.groupby(['yearmonth','weekday']).size().unstack(fill_value=0).reindex(columns=range(7),fill_value=0); om.columns=['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']; fig,ax=canvas(); heat(ax,om,'Pedidos únicos'); ax.set_title('Pedidos por mes y día de semana'); ax.tick_params(axis='y',labelsize=8); p=px.imshow(om,aspect='auto',labels=dict(x='Día de semana',y='Mes',color='Pedidos'))
    weekday=orders.groupby('weekday').size(); best=int(weekday.idxmax())
    register('N10','Heatmap temporal de pedidos',fig,p,'Se cuenta Orders.OrderID en la tabla de pedidos, una sola vez, por mes y día de semana. Se incluyen fines de semana con cero.',f'Hay {len(orders)} pedidos únicos. {om.columns[best]} acumula {weekday.max()} pedidos, el mayor conteo por día de semana.','Planificar personal para los días con más actividad de registro, contrastando pedidos y tiempo de procesamiento.','El conteo agregado no ajusta por cuántas veces aparece cada día en cada mes. No representa hora de compra ni fecha de entrega.',"orders.groupby([orders.OrderDate.dt.to_period('M'),\n                orders.OrderDate.dt.dayofweek]).size()")

def human_resources(h):
    fig,ax=canvas(); largest=h.department_name.value_counts().head(4).index
    for dep in largest: ax.hist(h[h.department_name==dep].salary,bins=np.arange(0,25001,2000),alpha=.45,label=dep)
    ax.set_xlabel('Salario registrado (unidad monetaria de muestra)'); ax.set_ylabel('Empleados'); ax.set_title('Distribución salarial en los 4 departamentos más poblados'); ax.legend(fontsize=8); p=px.histogram(h,x='salary',color='department_name',nbins=12,barmode='overlay',opacity=.6,labels={'salary':'Salario','department_name':'Departamento'})
    register('H01','Histograma salarial por departamento',fig,p,'La versión estática superpone cuatro departamentos por tamaño. La versión interactiva permite mostrar u ocultar todos los departamentos desde la leyenda.',f'Los {len(h)} empleados tienen salario mediano {cash(h.salary.median())}, promedio {cash(h.salary.mean())} y máximo {cash(h.salary.max())}.','Revisar bandas de compensación por puesto y departamento antes de explicar diferencias.','HR es una muestra académica y documenta salarios mensuales. La moneda no se atribuye; la dispersión no permite inferir discriminación o desempeño.',"px.histogram(h, x='salary', color='department_name',\n             nbins=12, barmode='overlay')")
    metrics=h.groupby('job_title').agg(Salario=('salary','mean'),Antigüedad=('tenure','mean'),Plantilla=('employee_id','size')); selected=metrics.nlargest(4,'Plantilla'); normalized=selected/metrics.max(); angles=np.linspace(0,2*np.pi,3,endpoint=False)
    fig=plt.figure(figsize=(10,5.6),layout='constrained'); ax=fig.add_subplot(111,projection='polar'); p=go.Figure()
    for i,(name,r) in enumerate(normalized.iterrows()):
        vals=r.values; ax.plot(np.r_[angles,angles[0]],np.r_[vals,vals[0]],label=name,color=COLORS[i]); p.add_trace(go.Scatterpolar(r=np.r_[vals,vals[0]],theta=list(normalized.columns)+[normalized.columns[0]],fill='toself',name=name))
    ax.set_xticks(angles,normalized.columns); ax.set_ylim(0,1); ax.legend(loc='upper right',bbox_to_anchor=(1.65,1),fontsize=9); ax.set_title('Perfil estructural del puesto (escala 0-1)'); p.update_layout(polar=dict(radialaxis=dict(range=[0,1],visible=True)))
    register('H02','Radar de perfiles de puesto',fig,p,'Se comparan cuatro puestos por tamaño. Salario medio, antigüedad media y plantilla se dividen por el máximo de cada variable en todos los puestos.',f'{selected.index[0]} es el puesto de mayor dotación entre los perfiles mostrados: {int(selected.iloc[0].Plantilla)} empleados.','Comparar dimensiones organizacionales y utilizar hover para inspeccionar perfiles relativos.','No existen evaluaciones de competencias en HR. El radar es un perfil estructural y no mide habilidad, calidad de trabajo ni puntuación de desempeño.',"metrics = h.groupby('job_title').agg(\n Salario=('salary','mean'), Antigüedad=('tenure','mean'),\n Plantilla=('employee_id','size'))\nnormalized = metrics / metrics.max()")
    ids=h.employee_id.astype(int).tolist(); manager=dict(zip(h.employee_id,h.manager_id)); children={i:[] for i in ids}; roots=[]
    for i in ids:
        m=manager[i]
        if pd.isna(m): roots.append(i)
        else: children[int(m)].append(i)
    positions={}; nextleaf=[0]
    def walk(i,depth):
        xs=[walk(c,depth+1) for c in children[i]]
        x=float(np.mean(xs)) if xs else nextleaf[0]
        if not xs: nextleaf[0]+=1
        positions[i]=(x,-depth); return x
    for i in roots: walk(i,0)
    fig,ax=canvas(); xe=[]; ye=[]
    for i in ids:
        if not pd.isna(manager[i]):
            a,b=positions[int(manager[i])],positions[i]; ax.plot([a[0],b[0]],[a[1],b[1]],c='#CBD5E1',lw=.8); xe +=[a[0],b[0],None]; ye +=[a[1],b[1],None]
    pos=np.array([positions[i] for i in ids]); ax.scatter(pos[:,0],pos[:,1],c=COLORS[0],s=20)
    for i in ids:
        x,y=positions[i]
        if y>=-1: ax.text(x,y+.08,str(i),fontsize=8,ha='center')
    ax.set_yticks(sorted(set(pos[:,1])),[f'Nivel {int(-v)}' for v in sorted(set(pos[:,1]))]); ax.set_xticks([]); ax.set_title(f'Organigrama completo: {len(ids)} nodos; etiquetas de primeros niveles')
    p=go.Figure([go.Scatter(x=xe,y=ye,mode='lines',line=dict(color='#CBD5E1'),hoverinfo='skip',showlegend=False),go.Scatter(x=pos[:,0],y=pos[:,1],mode='markers',text=(h.employee_id.astype(str)+' | '+h.first_name+' '+h.last_name+' | '+h.job_title),hovertemplate='%{text}<extra></extra>',showlegend=False)]); p.update_xaxes(visible=False); p.update_yaxes(title='Nivel jerárquico')
    register('H03','Organigrama interactivo',fig,p,'Se construye un árbol a partir de employee_id y manager_id. Se dibujan todos los empleados; el dashboard muestra nombre y puesto al pasar el cursor.',f'La estructura contiene {len(ids)} nodos, {len(ids)-len(roots)} relaciones y {len(roots)} raíz. La profundidad máxima es {int(-pos[:,1].min())} enlaces.','Inspeccionar amplitud de supervisión y cadenas de reporte antes de proponer cambios de estructura.','Una relación jerárquica no indica carga de trabajo ni autoridad informal. La coordenada horizontal sólo separa ramas del árbol.',"edges = h[['employee_id','manager_id']].dropna()\n# Posiciones calculadas por recorrido del árbol; hover por empleado.")
    loc=h.groupby(['city','department_name']).size().unstack(fill_value=0); fig,ax=canvas(); heat(ax,loc,'Empleados'); ax.tick_params(axis='x',labelsize=8); ax.set_title('Empleados por ciudad y departamento'); p=px.imshow(loc,aspect='auto',labels=dict(x='Departamento',y='Ciudad',color='Empleados'))
    city=h.city.value_counts()
    register('H04','Mapa de calor de dotación por ubicación',fig,p,'Se une employees con departments, locations, countries y regions mediante uniones izquierdas. Los empleados sin departamento conservan una categoría explícita.',f'{city.index[0]} concentra {city.iloc[0]} empleados. Hay {int((h.city=="Sin ubicación").sum())} empleado sin ubicación derivable.','Identificar ubicaciones con concentración de personal y revisar registros sin asignación organizacional.','La densidad aquí es un conteo, no empleados por superficie. La ubicación corresponde al departamento y no al domicilio personal.',"h.groupby(['city','department_name']).size().unstack(fill_value=0)")
    lv=list(h.level.cat.categories); arr=[h[h.level==n].salary for n in lv]; fig,ax=canvas(); ax.violinplot(arr,showmedians=True); ax.set_xticks(range(1,4),lv); ax.set_ylabel('Salario'); ax.set_title('Distribución salarial por antigüedad en la empresa'); p=px.violin(h,x='level',y='salary',box=True,points='all',labels={'level':'Antigüedad','salary':'Salario'})
    register('H05','Violín salarial por antigüedad',fig,p,'La antigüedad se calcula entre hire_date y 08/10/2026, en días / 365.25. Se crean tres bandas y se muestra una densidad estimada con mediana.',f'La antigüedad mediana es {h.tenure.median():.2f} años. Las bandas contienen '+', '.join(f'{n}: {len(a)}' for n,a in zip(lv,arr))+'.','Comparar salarios dentro del mismo puesto antes de interpretar el efecto de la antigüedad.','La antigüedad en la empresa no equivale a experiencia profesional total. La densidad depende de la muestra y del suavizado.',"h['tenure'] = (pd.Timestamp('2026-10-08') - h.hire_date).dt.days / 365.25\npx.violin(h, x='level', y='salary', box=True)")
    hist=read('hr_job_history'); names=dict(zip(read('hr_departments').department_id,read('hr_departments').department_name)); flows=[]
    for eid,g in hist.groupby('employee_id'):
        seq=g.sort_values('start_date').department_id.tolist()+h[h.employee_id==eid].department_id.tolist()
        for a,b in zip(seq,seq[1:]):
            if pd.notna(a) and pd.notna(b): flows.append((names[a],names[b]))
    flow=pd.DataFrame(flows,columns=['source','target']).value_counts().reset_index(name='value'); sources=list(flow.source.unique()); targets=list(flow.target.unique()); nodes=['Anterior: '+x for x in sources]+['Posterior: '+x for x in targets]; si=[sources.index(x) for x in flow.source]; ti=[len(sources)+targets.index(x) for x in flow.target]
    p=go.Figure(go.Sankey(node=dict(label=nodes,color=COLORS*3,pad=20),link=dict(source=si,target=ti,value=flow.value)))
    fig,ax=canvas(); sy={n:i for i,n in enumerate(sources)}; ty={n:i for i,n in enumerate(targets)}
    # Bandas del Sankey con espesor proporcional al conteo, extremos desplazados.
    for idx,r in flow.iterrows():
        y0=sy[r.source]/max(1,len(sources)-1); y1=ty[r.target]/max(1,len(targets)-1); w=.023*r.value
        verts=[(.18,y0-w),(.43,y0-w),(.57,y1-w),(.82,y1-w),(.82,y1+w),(.57,y1+w),(.43,y0+w),(.18,y0+w),(.18,y0-w)]
        codes=[MPath.MOVETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.LINETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.CLOSEPOLY]; ax.add_patch(PathPatch(MPath(verts,codes),color=COLORS[idx%len(COLORS)],alpha=.55))
        ax.text(.5,(y0+y1)/2,str(r.value),fontsize=8,ha='center')
    for n,i in sy.items(): ax.text(.17,i/max(1,len(sources)-1),n,ha='right',va='center',fontsize=9)
    for n,i in ty.items(): ax.text(.83,i/max(1,len(targets)-1),n,va='center',fontsize=9)
    ax.set_xlim(-.13,1.13); ax.set_ylim(-.15,1.15); ax.axis('off'); ax.set_title('Transiciones de departamento registradas (incluye permanencias)')
    changed=sum(a!=b for a,b in flows)
    register('H06','Sankey de cambios de departamento',fig,p,'Por empleado se ordena job_history por start_date. Cada departamento se conecta con el siguiente registro y, al final, con el departamento actual. Los lados separan estado anterior y posterior.',f'Se reconstruyen {len(flows)} transiciones: {changed} cambian de departamento y {len(flows)-changed} permanecen en el mismo. El histórico contiene {hist.employee_id.nunique()} empleados.','Usar el flujo para formular preguntas sobre movilidad interna y cambios de puesto.','No existen bajas ni una población histórica completa. No se estima rotación de salida; un enlace al estado actual no documenta su fecha exacta.',"seq = historial.sort_values('start_date').department_id.tolist()\nseq += [departamento_actual]\ntransiciones = list(zip(seq, seq[1:]))")
    counts=h.department_name.value_counts(); fig,ax=canvas()
    for i,(dep,g) in enumerate(h.groupby('department_name')): ax.scatter(g.tenure,g.salary,s=counts[dep]*5,alpha=.5,label=dep,c=COLORS[i%len(COLORS)])
    ax.set_xlabel('Antigüedad (años)'); ax.set_ylabel('Salario'); ax.set_title('Salario, antigüedad y departamento'); ax.legend(fontsize=7,ncol=3,loc='upper center',bbox_to_anchor=(.5,-.18)); hb=h.assign(department_size=h.department_name.map(counts)); p=px.scatter(hb,x='tenure',y='salary',color='department_name',size='department_size',hover_name='last_name',labels={'tenure':'Antigüedad (años)','salary':'Salario','department_name':'Departamento','department_size':'Dotación del departamento'})
    register('H07','Burbujas: salario y antigüedad',fig,p,'Cada punto es un empleado. El área de burbuja representa tamaño del departamento; el color representa departamento. Las coordenadas son antigüedad y salario.',f'La correlación de Pearson entre antigüedad y salario es {h.tenure.corr(h.salary):.3f}.','Examinar casos de compensación alta o baja dentro de grupos de puestos comparables.','El área repite el tamaño del departamento para cada empleado y no debe sumarse. La correlación está afectada por puesto, jerarquía y composición.',"h['department_size'] = h.department_name.map(h.department_name.value_counts())\npx.scatter(h, x='tenure', y='salary', size='department_size',\n           color='department_name')")
    months=h.hire_date.dt.month; grid=np.linspace(.5,12.5,300); kde=gaussian_kde(months,bw_method=.25); fig,ax=canvas(); ax.plot(grid,kde(grid)); ax.fill_between(grid,kde(grid),alpha=.2); ax.set_xticks(range(1,13),['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']); ax.set_ylabel('Densidad estimada'); ax.set_title('Mes de contratación (todos los años combinados)'); p=go.Figure([go.Scatter(x=grid,y=kde(grid),fill='tozeroy',name='Densidad KDE')]); p.update_xaxes(title='Mes',tickvals=list(range(1,13))); p.update_yaxes(title='Densidad')
    mcount=months.value_counts()
    register('H08','Densidad de contrataciones por mes',fig,p,'Se combinan meses de contratación de todos los años. La curva aplica KDE con ancho relativo 0.25; es una aproximación suavizada de una variable discreta.',f'El mes con más contrataciones observadas es {int(mcount.idxmax())}, con {int(mcount.max())} empleados del catálogo actual.','Examinar el conteo por año y mes antes de atribuir estacionalidad al proceso de contratación.','Enero y diciembre son adyacentes en un calendario, pero esta KDE no es circular. Sólo incluye empleados actuales y no permite estimar tasa histórica de contratación.',"months = h.hire_date.dt.month\nkde = gaussian_kde(months, bw_method=0.25)")
    reg=h.region_name.value_counts(); fig,ax=canvas(); ax.pie(reg,labels=reg.index,autopct='%1.0f%%',wedgeprops={'width':.42},colors=COLORS); ax.set_title('Empleados por región del departamento'); ax.text(0,0,str(len(h))+'\nempleados',ha='center',va='center'); p=px.pie(names=reg.index,values=reg.values,hole=.55,color_discrete_sequence=COLORS)
    register('H09','Donut de empleados por región',fig,p,'Cada empleado se asigna a la región de su departamento mediante la cadena de ubicaciones. Se conserva Sin región para el registro sin departamento.',f'{reg.index[0]} concentra {reg.iloc[0]} de {len(h)} empleados ({100*reg.iloc[0]/len(h):.1f}%).','Evaluar concentración territorial del catálogo organizacional y calidad de asignaciones.','La región es una categoría geográfica corporativa de esta versión de HR. No aporta nacionalidad, edad, sexo ni otras variables demográficas personales.',"h.region_name.fillna('Sin región').value_counts()")
    jobs=read('hr_jobs').set_index('job_id'); chain=['IT_PROG','IT_PROG','AD_VP','AD_PRES']; vals=[float(jobs.loc[k,'min_salary'] if i==0 else jobs.loc[k,'max_salary']) for i,k in enumerate(chain)]; labels=['Mín. IT_PROG','Máx. IT_PROG','Máx. AD_VP','Máx. AD_PRES']; delta=np.diff([0]+vals)
    fig,ax=canvas(); ax.bar(range(4),delta,bottom=[0]+vals[:-1],color=COLORS[:4]);
    for i,v in enumerate(vals): ax.text(i,v+600,cash(v),ha='center',fontsize=9)
    ax.set_xticks(range(4),labels); ax.set_ylabel('Límites de bandas salariales'); ax.set_title('Escenario de bandas, sin historial salarial individual'); p=go.Figure(go.Waterfall(x=labels,y=delta,measure=['absolute','relative','relative','relative'],text=[cash(v) for v in vals],textposition='outside')); p.update_yaxes(title='Límites de bandas salariales')
    register('H10','Waterfall de bandas salariales: escenario ilustrativo',fig,p,'Se encadenan el mínimo y máximo de IT_PROG y los máximos de AD_VP y AD_PRES. Cada escalón representa diferencia entre límites de bandas definidos en jobs.',f'El escenario va de {cash(vals[0])} a {cash(vals[-1])}; la diferencia es {cash(vals[-1]-vals[0])}.','Ilustrar cómo se comparan bandas de puestos; reemplazarlo por un historial real si se desea analizar progresión de una carrera.','No representa ascensos observados, salarios pasados ni trayectoria de un empleado. La secuencia de puestos es hipotética y las bandas son datos oficiales.',"jobs = read('hr_jobs').set_index('job_id')\nlimits = [jobs.loc['IT_PROG','min_salary'], jobs.loc['IT_PROG','max_salary'],\n          jobs.loc['AD_VP','max_salary'], jobs.loc['AD_PRES','max_salary']]")

def sensors(s):
    temp=s[s.type=='temperatura']; daily=temp.groupby(['date','city'],as_index=False).value.mean(); fig,ax=canvas()
    for city,g in daily.groupby('city'): ax.plot(g.date,g.value,label=city)
    ax.set_ylabel('Temperatura media diaria (°C)'); ax.set_title('Temperatura por ciudad, septiembre de 2026'); ax.tick_params(axis='x',rotation=30); ax.legend(); p=px.line(daily,x='date',y='value',color='city',labels={'value':'Temperatura media (°C)','date':'Fecha local','city':'Ciudad'})
    means=temp.groupby('city').value.mean()
    register('S01','Serie temporal de temperatura por ciudad',fig,p,'Se promedian dos estaciones y 24 lecturas horarias por día y ciudad. La fecha se obtiene después de convertir UTC a America/Santo_Domingo.',f'{means.idxmax()} tiene la mayor temperatura media: {means.max():.2f} °C.','Inspeccionar cambios diarios y confirmar si responden a señales persistentes o a puntos anómalos.','Todas las lecturas son sintéticas; las diferencias entre ciudades se definieron en el generador y no describen el clima real.',"temp = s[s.type == 'temperatura']\ndaily = temp.groupby(['date','city'], as_index=False).value.mean()")
    geo=s.groupby(['city','station','latitude','longitude'],as_index=False).agg(readings=('value','size')); fig,ax=canvas(); im=ax.scatter(geo.longitude,geo.latitude,c=geo.readings,cmap='YlGnBu',s=240,edgecolor='black',vmin=0,vmax=geo.readings.max()); plt.colorbar(im,ax=ax,label='Lecturas por estación');
    for city,g in geo.groupby('city'): ax.annotate(city,(g.longitude.mean(),g.latitude.mean()),xytext=(6,14),textcoords='offset points',fontsize=9)
    ax.set_xlabel('Longitud (°)'); ax.set_ylabel('Latitud (°)'); ax.set_title('Mapa geográfico de intensidad por estación'); geo['etiqueta']=geo.city.where(~geo.city.duplicated(),'')  # una etiqueta por ciudad (dos estaciones cada una)
    p=px.scatter(geo,x='longitude',y='latitude',color='readings',text='etiqueta',hover_data={'city':True,'etiqueta':False},hover_name='station',range_color=(0,float(geo.readings.max())),color_continuous_scale='YlGnBu',labels={'readings':'Lecturas','longitude':'Longitud (°)','latitude':'Latitud (°)','city':'Ciudad'})
    # Coordenadas en ejes con la misma escala: funciona sin mapa base externo ni WebGL.
    p.update_traces(marker={'size':26,'line':{'width':1,'color':'#1f2937'}},textposition='top center')
    p.update_yaxes(scaleanchor='x',scaleratio=1)
    register('S02','Mapa de calor geográfico de lecturas',fig,p,'Se agregan lecturas por coordenada de estación. La figura estática ubica puntos coloreados en latitud/longitud; el dashboard muestra las estaciones en longitud/latitud con la misma escala, coloreadas por lecturas, sin depender de un mapa externo.',f'Las seis estaciones tienen {int(geo.readings.min()):,} lecturas cada una; la cobertura de observación es uniforme.','Utilizar el mapa para reconocer distribución de estaciones y revisar diferencias de cobertura cuando se incorporen datos reales.','El mapa representa conteo y no temperatura. Las coordenadas de estaciones son ilustrativas; no corresponden a instalaciones verificadas.',"geo = s.groupby(['city','station','latitude','longitude'],\n as_index=False).agg(readings=('value','size'))")
    types=['temperatura','humedad','co2']; units=['°C','%','ppm']; fig,axes=plt.subplots(1,3,figsize=(10,5.6),layout='constrained'); p=make_subplots(rows=1,cols=3,subplot_titles=types)
    for i,(typ,unit) in enumerate(zip(types,units)):
        a=s[s.type==typ].value; axes[i].violinplot(a,showmedians=True); axes[i].set_title(typ); axes[i].set_ylabel(unit); axes[i].set_xticks([]); p.add_trace(go.Violin(y=a,box_visible=True,name=typ,points=False),row=1,col=i+1); p.update_yaxes(title=unit,row=1,col=i+1)
    register('S03','Violines por tipo de sensor',fig,p,'Se dibujan tres distribuciones en paneles con escalas y unidades independientes. Las colas incluyen anomalías inyectadas.',f'Las medianas son temperatura {temp.value.median():.2f} °C, humedad {s[s.type=="humedad"].value.median():.2f}% y CO2 {s[s.type=="co2"].value.median():.2f} ppm.','Comparar dispersión dentro de cada magnitud y revisar extremos con el detector robusto.','Las variables tienen unidades distintas. Las alturas entre paneles no deben compararse; la forma depende del ancho de suavizado.',"for typ in ['temperatura','humedad','co2']:\n    values = s.loc[s.type == typ, 'value']\n    # Un panel independiente y su unidad para cada magnitud.")
    wide=s.pivot(index=['station','timestamp'],columns='type',values='value').reset_index(); corr=wide[types].corr(); fig,axes=plt.subplots(3,3,figsize=(10,6),layout='constrained')
    for i,y in enumerate(types):
        for j,x in enumerate(types):
            if i==j: axes[i,j].hist(wide[x],bins=25,color=COLORS[j])
            else: axes[i,j].scatter(wide[x],wide[y],s=2,alpha=.1,color=COLORS[j])
            if i==2: axes[i,j].set_xlabel(x+' ('+units[j]+')')
            if j==0: axes[i,j].set_ylabel(y+' ('+units[i]+')')
            if i==j:
                axes[i,j].set_ylabel('Frecuencia',fontsize=8)
                axes[i,j].set_title(x+' ('+units[j]+')',fontsize=9)
    p=px.scatter_matrix(wide,dimensions=types,color='station',opacity=.25); p.update_traces(diagonal_visible=False)
    register('S04','Matriz de dispersión entre sensores',fig,p,'Se alinea cada estación y timestamp antes de pivotar tipos. No se correlacionan listas de lecturas sin correspondencia temporal.',f'La correlación temperatura-humedad es {corr.loc["temperatura","humedad"]:.3f}; temperatura-CO2 es {corr.loc["temperatura","co2"]:.3f}.','Inspeccionar dependencias y diferencias entre estaciones, y recalcular correlaciones excluyendo anomalías para analizar sensibilidad.','La relación inversa entre humedad y temperatura fue introducida por el generador. Los puntos extremos alteran Pearson y no constituyen evidencia física de campo.',"wide = s.pivot(index=['station','timestamp'],\n               columns='type', values='value')\ncorrelations = wide.corr()")
    counts=s.groupby(['date','city']).size().unstack(); fig,ax=canvas(); ax.stackplot(counts.index,counts.T.values,labels=counts.columns); ax.set_ylabel('Número de lecturas por día'); ax.set_title('Composición diaria de lecturas por ciudad'); ax.legend(); ax.tick_params(axis='x',rotation=30); long=counts.reset_index().melt('date',var_name='Ciudad',value_name='Lecturas'); p=px.area(long,x='date',y='Lecturas',color='Ciudad',labels={'date':'Fecha local'})
    register('S05','Áreas apiladas por ubicación',fig,p,'Se apilan conteos diarios por ciudad. Se usa conteo para evitar sumar temperatura, humedad y CO2, magnitudes incompatibles.',f'Cada ciudad aporta {int(counts.sum().iloc[0]):,} lecturas en 30 días; la participación diaria es 33.3% por ciudad.','Identificar pérdida de cobertura si una banda disminuye en un despliegue real.','La estabilidad procede del muestreo sintético uniforme. La suma representa eventos y no intensidad de una variable física.',"counts = s.groupby(['date','city']).size().unstack(fill_value=0)")
    station='SDQ-1-temperatura'; one=s[s.sensor_id==station]; det=one[one.detected]; fig,ax=canvas(); ax.plot(one.timestamp,one.value,lw=.8,label='Lectura'); ax.scatter(det.timestamp,det.value,c=COLORS[4],s=35,marker='x',label='Alerta MAD'); ax.set_ylabel('Temperatura (°C)'); ax.set_title('Anomalías robustas con patrón horario como referencia'); ax.tick_params(axis='x',rotation=30); ax.legend(); p=go.Figure([go.Scatter(x=one.timestamp,y=one.value,name='Lectura'),go.Scatter(x=det.timestamp,y=det.value,name='Alerta MAD',mode='markers',marker=dict(symbol='x',color=COLORS[4],size=10))]); p.update_yaxes(title='Temperatura (°C)'); p.update_xaxes(title='Fecha local')
    tp=int((s.detected&s.injected_anomaly).sum()); fp=int((s.detected&~s.injected_anomaly).sum()); fn=int((~s.detected&s.injected_anomaly).sum()); precision=tp/(tp+fp); recall=tp/(tp+fn)
    register('S06','Detección de anomalías con MAD',fig,p,'Por sensor y hora del día se calcula mediana y MAD. Se alerta si |valor - mediana| / (1.4826 × MAD) > 3.5. La etiqueta inyectada sólo se usa para evaluar.',f'En las {len(s):,} lecturas se detectan {int(s.detected.sum())} alertas: {tp} verdaderos positivos, {fp} falsos positivos y {fn} falsos negativos. Precisión {precision:.1%}; sensibilidad {recall:.1%}.','Revisar alertas antes de eliminar datos y calibrar el umbral con una ventana histórica independiente.','La referencia usa todo septiembre: es detección retrospectiva, no validación predictiva. En producción debe entrenarse sobre datos previos y controlar MAD igual a cero.',"s['score'] = abs(s.value - s.baseline) / (1.4826 * s.mad)\ns['detected'] = s.score > 3.5\n# injected_anomaly NO participa en la regla.")
    dc=s.groupby('date').detected.sum(); start=pd.Timestamp('2026-09-01'); mat=np.full((5,7),np.nan)
    for date,v in dc.items(): day=pd.Timestamp(date); offset=(day-start).days+start.dayofweek; mat[offset//7,offset%7]=v
    fig,ax=canvas(); im=ax.imshow(mat,cmap='YlOrRd',aspect='auto'); ax.set_xticks(range(7),['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']); ax.set_yticks(range(5),[f'Semana {i+1}' for i in range(5)]); plt.colorbar(im,ax=ax,label='Alertas diarias')
    for date,v in dc.items(): day=pd.Timestamp(date); off=(day-start).days+start.dayofweek; ax.text(off%7,off//7,f'{day.day}\n{v} alertas',ha='center',va='center',fontsize=9)
    ax.set_title('Calendario de alertas, septiembre de 2026'); p=px.imshow(mat,aspect='auto',x=['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'],y=[f'Semana {i+1}' for i in range(5)],labels=dict(color='Alertas'))
    register('S07','Calendario de patrones diarios',fig,p,'Se suman alertas por día local y se organizan en semanas de lunes a domingo. Celdas fuera de septiembre permanecen vacías.',f'El mayor conteo corresponde al {dc.idxmax()}: {int(dc.max())} alertas sobre 432 lecturas diarias.','Comparar alertas diarias con volumen de lecturas para localizar jornadas de revisión.','Sólo hay un mes de datos simulados. El máximo no confirma un patrón semanal estable ni una falla real.',"daily_alerts = s.groupby('date').detected.sum()\n# Matriz calendario con huecos fuera del mes.")
    sensors=s[['sensor_id','station','type']].drop_duplicates(); stations=sorted(sensors.station.unique()); positions={}; edges=[]
    for k,st in enumerate(stations):
        center=np.array([np.cos(k*np.pi/3),np.sin(k*np.pi/3)])*2; group=sensors[sensors.station==st]
        for j,(_,r) in enumerate(group.iterrows()): positions[r.sensor_id]=center+.38*np.array([np.cos(j*2*np.pi/3),np.sin(j*2*np.pi/3)])
        ns=group.sensor_id.tolist(); edges+= [(a,b) for i,a in enumerate(ns) for b in ns[i+1:]]
    fig,ax=canvas(); xe=[];ye=[]
    for a,b in edges:
        pa,pb=positions[a],positions[b]; ax.plot([pa[0],pb[0]],[pa[1],pb[1]],color='#CBD5E1'); xe +=[pa[0],pb[0],None]; ye +=[pa[1],pb[1],None]
    for typ in types:
        group=sensors[sensors.type==typ]; coords=np.array([positions[n] for n in group.sensor_id]); ax.scatter(coords[:,0],coords[:,1],label=typ,s=55)
    for k,st in enumerate(stations): center=np.array([np.cos(k*np.pi/3),np.sin(k*np.pi/3)])*2; ax.text(center[0],center[1]+.6,st,ha='center')
    ax.set_xlim(-2.9,2.9); ax.set_ylim(-2.9,2.9); ax.axis('off'); ax.set_aspect('equal'); ax.legend(loc='upper right'); ax.set_title('Relación de co-localización: sensores de la misma estación'); ids=sensors.sensor_id.tolist(); coords=np.array([positions[n] for n in ids]); p=go.Figure([go.Scatter(x=xe,y=ye,mode='lines',hoverinfo='skip',showlegend=False,line=dict(color='#CBD5E1')),go.Scatter(x=coords[:,0],y=coords[:,1],text=ids,mode='markers',hovertemplate='%{text}<extra></extra>',marker=dict(size=12,color=[COLORS[types.index(t)] for t in sensors.type]),showlegend=False)]); p.update_xaxes(visible=False); p.update_yaxes(visible=False,scaleanchor='x')
    register('S08','Red de relaciones entre sensores',fig,p,'Se crea un enlace entre dos sensores cuando comparten station. La posición es un diseño de red; no expresa coordenadas geográficas.',f'La red tiene {len(ids)} sensores, {len(edges)} relaciones y seis grupos de tres sensores.','Examinar qué magnitudes se observan conjuntamente y organizar validaciones por estación.','La relación es de co-localización definida en el esquema sintético. No representa conexiones físicas, tráfico de red ni causalidad.',"nodes = s[['sensor_id','station','type']].drop_duplicates()\n# Enlace sólo si dos nodos comparten station.")
    sample=temp.iloc[::12].copy(); stationindex={st:i for i,st in enumerate(stations)}; sample['station_index']=sample.station.map(stationindex); sample['elapsed']=(sample.timestamp-sample.timestamp.min()).dt.total_seconds()/3600
    fig=plt.figure(figsize=(10,5.6),layout='constrained'); ax=fig.add_subplot(111,projection='3d'); im=ax.scatter(sample.elapsed,sample.station_index,sample.value,c=sample.value,cmap='YlOrRd',s=12); ax.set_xlabel('Horas transcurridas'); ax.set_ylabel('Estación (índice)'); ax.set_zlabel('Temperatura (°C)'); ax.set_yticks(range(6),stations,fontsize=8); ax.set_title('Temperatura, estación y tiempo (muestra sistemática)'); p=px.scatter_3d(sample,x='elapsed',y='station_index',z='value',color='city',hover_name='station',labels={'elapsed':'Horas','station_index':'Estación (índice)','value':'Temperatura (°C)','city':'Ciudad'})
    register('S09','Dispersión 3D: valor, ubicación y tiempo',fig,p,'Se usa sólo temperatura para mantener una unidad coherente. Se toma una fila de cada doce y se codifica la estación como índice categórico.',f'El gráfico contiene {len(sample)} puntos de {len(temp):,} lecturas de temperatura.','Rotar y explorar el gráfico para localizar valores altos y comparar con las series temporales completas.','La distancia entre índices de estación no es distancia geográfica. El muestreo reduce carga y puede omitir anomalías; el detector utiliza todas las lecturas.',"sample = temp.iloc[::12].copy()\npx.scatter_3d(sample, x='elapsed', y='station_index', z='value',\n              color='city', hover_name='station')")
    # Reproducción de una ventana histórica; nunca se presenta como conexión en vivo.
    frame=temp[temp.station=='SDQ-1'].tail(48); fig,ax=canvas(); ax.plot(frame.timestamp,frame.value,'o-',ms=3); ax.axhline(35,color=COLORS[4],ls='--',label='Umbral ilustrativo 35 °C'); ax.set_ylabel('Temperatura (°C)'); ax.set_title('Ventana de 48 horas de reproducción histórica'); ax.tick_params(axis='x',rotation=30); ax.legend(); p=go.Figure(go.Scatter(x=frame.timestamp,y=frame.value,mode='lines+markers',name='SDQ-1')); p.update_yaxes(title='Temperatura (°C)'); p.update_xaxes(title='Fecha histórica local')
    register('S10','Dashboard de monitoreo simulado',fig,p,'El dashboard incorpora controles de reproducir, pausar y reiniciar. Cada segundo agrega una lectura histórica de SDQ-1 a una ventana de 48 puntos.',f'La última lectura histórica de SDQ-1 es {frame.iloc[-1].value:.2f} °C, registrada el {frame.iloc[-1].timestamp.strftime("%d/%m/%Y %H:%M")}.','Usar la reproducción para probar controles, alertas visuales y actualización de una serie antes de conectar un flujo real.','Un segundo de reproducción equivale a una hora histórica. No hay streaming desde MongoDB ni medición ambiental en vivo. El umbral de 35 °C es ilustrativo.',"history = temp[temp.station == 'SDQ-1']\n# JavaScript avanza una lectura por segundo y conserva 48 puntos.")
    return dict(tp=tp,fp=fp,fn=fn,precision=precision,recall=recall,alerts=int(s.detected.sum()),injected=int(s.injected_anomaly.sum()))

def main():
    for folder in ['figuras','dashboard']: (ROOT/folder).mkdir(exist_ok=True)
    orders,nw,products,customers,suppliers,hr,s=load()
    northwind(orders,nw,products,customers,suppliers); human_resources(hr); detector=sensors(s)
    assert len(META)==30 and len(FIGS)==30
    (ROOT/'docs/visualizaciones.json').write_text(json.dumps(META,ensure_ascii=False,indent=2))
    summary={'nw':{'orders':len(orders),'lines':len(nw),'customers':len(customers),'active_customers':nw.CustomerID.nunique(),'net':float(nw.net.sum()),'gross':float(nw.gross.sum()),'discount_amount':float((nw.gross-nw.net).sum()),'period':[str(orders.OrderDate.min().date()),str(orders.OrderDate.max().date())]},'hr':{'employees':len(hr),'salary_mean':float(hr.salary.mean()),'salary_median':float(hr.salary.median()),'unassigned':int(hr.department_id.isna().sum()),'sum_salary':float(hr.salary.sum())},'sensors':{'rows':len(s),'stations':s.station.nunique(),'sensors':s.sensor_id.nunique(),**detector}}
    (ROOT/'docs/resultados.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
