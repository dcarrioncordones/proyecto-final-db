-- Ejecutar como HR; referencia fija 2026-10-08; sólo lectura.
-- H01: salario por departamento; NULL se conserva como Sin departamento.
SELECT e.employee_id,NVL(d.department_name,'Sin departamento') AS departamento,e.salary
FROM employees e LEFT JOIN departments d ON d.department_id=e.department_id;

-- H02: perfil estructural. No hay competencias en HR.
SELECT j.job_title,AVG(e.salary) AS salario_medio,
AVG((DATE '2026-10-08'-e.hire_date)/365.25) AS antiguedad_media,COUNT(*) AS plantilla
FROM employees e JOIN jobs j ON j.job_id=e.job_id GROUP BY j.job_title;

-- H03: organigrama, una relación por empleado.
SELECT employee_id,manager_id,first_name,last_name,job_id FROM employees ORDER BY employee_id;

-- H04: dotación por ciudad y departamento.
SELECT NVL(l.city,'Sin ubicación') AS ciudad,NVL(d.department_name,'Sin departamento') AS departamento,
COUNT(*) AS empleados FROM employees e LEFT JOIN departments d ON d.department_id=e.department_id
LEFT JOIN locations l ON l.location_id=d.location_id GROUP BY l.city,d.department_name;

-- H05: salario por antigüedad, proxy de permanencia en la empresa.
SELECT employee_id,salary,(DATE '2026-10-08'-hire_date)/365.25 AS antiguedad FROM employees;

-- H06: histórico y asignación actual; reconstruir sucesiones por employee_id en Python.
SELECT employee_id,start_date,end_date,job_id,department_id FROM job_history ORDER BY employee_id,start_date;
SELECT employee_id,department_id FROM employees;

-- H07: salario, antigüedad y tamaño departamental.
SELECT employee_id,salary,(DATE '2026-10-08'-hire_date)/365.25 AS antiguedad,
department_id,COUNT(*) OVER(PARTITION BY department_id) AS plantilla_departamento FROM employees;

-- H08: meses de contratación; KDE se calcula en Python.
SELECT EXTRACT(MONTH FROM hire_date) AS mes,COUNT(*) AS contrataciones
FROM employees GROUP BY EXTRACT(MONTH FROM hire_date) ORDER BY mes;

-- H09: región de departamento, no nacionalidad personal.
SELECT NVL(r.region_name,'Sin región') AS region,COUNT(*) AS empleados
FROM employees e LEFT JOIN departments d ON d.department_id=e.department_id
LEFT JOIN locations l ON l.location_id=d.location_id LEFT JOIN countries c ON c.country_id=l.country_id
LEFT JOIN regions r ON r.region_id=c.region_id GROUP BY r.region_name;

-- H10: escenario de bandas de puestos. No hay sueldos históricos individuales.
SELECT job_id,job_title,min_salary,max_salary FROM jobs
WHERE job_id IN ('IT_PROG','AD_VP','AD_PRES') ORDER BY max_salary;
