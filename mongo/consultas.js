// Ejecutar con mongosh sobre bigdata_final. Requiere MongoDB >=5.0 por $dateTrunc.
// Colección sensores_datos, timestamp BSON Date, zona local explícita.
const c = db.getSiblingDB('bigdata_final').sensores_datos;
const tz = 'America/Santo_Domingo';
// S01: media diaria por ciudad, sólo temperatura.
c.aggregate([{$match:{type:'temperatura'}},{$group:{_id:{date:{$dateTrunc:{date:'$timestamp',unit:'day',timezone:tz}},city:'$city'},mean:{$avg:'$value'},n:{$sum:1}}},{$sort:{'_id.date':1}}]);
// S02: intensidad de lecturas por ubicación.
c.aggregate([{$group:{_id:{city:'$city',station:'$station',lat:'$latitude',lon:'$longitude'},n:{$sum:1}}}]);
// S03: observaciones separadas por tipo y unidad, nunca sumar magnitudes diferentes.
c.find({},{_id:0,type:1,value:1,unit:1});
// S04: alineación por estación y timestamp; pivotar types en Python.
c.aggregate([{$group:{_id:{station:'$station',timestamp:'$timestamp'},readings:{$push:{type:'$type',value:'$value'}}}},{$sort:{'_id.timestamp':1}}]);
// S05: conteo de eventos diarios por ciudad.
c.aggregate([{$group:{_id:{date:{$dateTrunc:{date:'$timestamp',unit:'day',timezone:tz}},city:'$city'},n:{$sum:1}}},{$sort:{'_id.date':1}}]);
// S06: series para mediana/MAD por sensor y hora local en Python.
c.aggregate([{$project:{_id:0,sensor_id:1,value:1,timestamp:1,hour:{$hour:{date:'$timestamp',timezone:tz}}}},{$sort:{sensor_id:1,timestamp:1}}]);
// S07: datos para calendario. Alertas se derivan en Python, no existen en la colección original.
c.find({},{_id:0,timestamp:1,sensor_id:1,value:1});
// S08: co-localización, no conectividad física.
c.aggregate([{$group:{_id:{sensor_id:'$sensor_id',station:'$station',type:'$type'}}}]);
// S09: sólo temperatura, muestreo sistemático reproducible en Python.
c.find({type:'temperatura'},{_id:0,station:1,city:1,value:1,timestamp:1}).sort({station:1,timestamp:1});
// S10: reproducción histórica, consulta de últimas 48 lecturas.
c.find({sensor_id:'SDQ-1-temperatura'},{_id:0,value:1,timestamp:1}).sort({timestamp:-1}).limit(48);
