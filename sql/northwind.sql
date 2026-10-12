-- Ejecutar en Northwind; consultas de sólo lectura.
-- La vista es opcional: se representa mediante CTE en cada consulta que la necesite.
-- Base reutilizable para visualizaciones N01-N06 y N09.
-- El precio histórico se toma de Order Details, no de Products.
-- N01: ventas mensuales y media móvil de 3 meses.
WITH mensual AS (
 SELECT DATEFROMPARTS(YEAR(o.OrderDate),MONTH(o.OrderDate),1) AS mes,
 SUM(CAST(d.UnitPrice AS decimal(18,4))*d.Quantity*(1-CAST(d.Discount AS decimal(9,4)))) AS neto
 FROM dbo.Orders o JOIN dbo.[Order Details] d ON o.OrderID=d.OrderID
 GROUP BY YEAR(o.OrderDate), MONTH(o.OrderDate))
SELECT mes,neto,CASE WHEN COUNT(*) OVER(ORDER BY mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)=3
 THEN AVG(neto) OVER(ORDER BY mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) END AS media_3m
FROM mensual ORDER BY mes;

-- N02: categoría por país del cliente; filtrar top 8 en Python.
SELECT ca.CategoryName,c.Country,SUM(d.UnitPrice*d.Quantity*(1-d.Discount)) AS neto
FROM dbo.[Order Details] d JOIN dbo.Orders o ON d.OrderID=o.OrderID
JOIN dbo.Products p ON d.ProductID=p.ProductID JOIN dbo.Categories ca ON ca.CategoryID=p.CategoryID
JOIN dbo.Customers c ON c.CustomerID=o.CustomerID GROUP BY ca.CategoryName,c.Country;

-- N03: top clientes por importe neto.
SELECT TOP (10) c.CustomerID,c.CompanyName,SUM(d.UnitPrice*d.Quantity*(1-d.Discount)) AS neto
FROM dbo.Orders o JOIN dbo.[Order Details] d ON d.OrderID=o.OrderID
JOIN dbo.Customers c ON c.CustomerID=o.CustomerID
GROUP BY c.CustomerID,c.CompanyName ORDER BY neto DESC,c.CustomerID;

-- N04: trimestre; cobertura parcial se documenta en el informe.
SELECT YEAR(o.OrderDate) AS anio,DATEPART(QUARTER,o.OrderDate) AS trimestre,
SUM(d.UnitPrice*d.Quantity*(1-d.Discount)) AS neto
FROM dbo.Orders o JOIN dbo.[Order Details] d ON d.OrderID=o.OrderID
GROUP BY YEAR(o.OrderDate),DATEPART(QUARTER,o.OrderDate) ORDER BY anio,trimestre;

-- N05: treemap; ingresos, no utilidad.
SELECT ca.CategoryName,p.ProductName,SUM(d.UnitPrice*d.Quantity*(1-d.Discount)) AS neto
FROM dbo.[Order Details] d JOIN dbo.Products p ON p.ProductID=d.ProductID
JOIN dbo.Categories ca ON ca.CategoryID=p.CategoryID GROUP BY ca.CategoryName,p.ProductName;

-- N06: observaciones para dispersión, una fila por línea.
SELECT d.OrderID,d.ProductID,d.Discount,d.Quantity,ca.CategoryName
FROM dbo.[Order Details] d JOIN dbo.Products p ON p.ProductID=d.ProductID
JOIN dbo.Categories ca ON ca.CategoryID=p.CategoryID;

-- N07: catálogo de clientes (incluye aquellos sin pedidos).
SELECT Country,COUNT(*) AS clientes FROM dbo.Customers GROUP BY Country ORDER BY clientes DESC;

-- N08: precios del catálogo por proveedor.
SELECT s.CompanyName,p.ProductID,p.UnitPrice FROM dbo.Products p
JOIN dbo.Suppliers s ON s.SupplierID=p.SupplierID;

-- N09: acumulado individual, apilar en Python.
WITH mensual AS (
 SELECT o.EmployeeID,DATEFROMPARTS(YEAR(o.OrderDate),MONTH(o.OrderDate),1) AS mes,
 SUM(d.UnitPrice*d.Quantity*(1-d.Discount)) AS neto
 FROM dbo.Orders o JOIN dbo.[Order Details] d ON d.OrderID=o.OrderID
 GROUP BY o.EmployeeID,YEAR(o.OrderDate),MONTH(o.OrderDate))
SELECT EmployeeID,mes,neto,SUM(neto) OVER(PARTITION BY EmployeeID ORDER BY mes ROWS UNBOUNDED PRECEDING) AS acumulado
FROM mensual ORDER BY EmployeeID,mes;

-- N10: no unir líneas; lunes=0 independientemente de SET DATEFIRST.
SELECT YEAR(OrderDate) AS anio,MONTH(OrderDate) AS mes,
((DATEDIFF(DAY,CONVERT(date,'19000101',112),OrderDate)%7)+7)%7 AS dia_semana,
COUNT(*) AS pedidos FROM dbo.Orders GROUP BY YEAR(OrderDate),MONTH(OrderDate),
((DATEDIFF(DAY,CONVERT(date,'19000101',112),OrderDate)%7)+7)%7 ORDER BY anio,mes,dia_semana;
