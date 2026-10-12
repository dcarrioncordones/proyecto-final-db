// Sólo ejecutar en una base de laboratorio nueva. No borra ni reemplaza documentos.
const lab = db.getSiblingDB('bigdata_final');
if (!lab.getCollectionNames().includes('sensores_datos')) {
  lab.createCollection('sensores_datos', {validator:{$jsonSchema:{bsonType:'object',required:['timestamp','sensor_id','station','city','type','value','unit'],properties:{timestamp:{bsonType:'date'},value:{bsonType:['double','int','long','decimal']},sensor_id:{bsonType:'string'}}}}});
}
lab.sensores_datos.createIndex({sensor_id:1,timestamp:1},{unique:true});
lab.sensores_datos.createIndex({type:1,timestamp:1,city:1});
