// Se ejecuta dentro de bigdata-mongodb; las credenciales no se imprimen.
const user=process.env.MONGO_INITDB_ROOT_USERNAME;
const password=encodeURIComponent(process.env.MONGO_INITDB_ROOT_PASSWORD);
const connection=new Mongo(`mongodb://${user}:${password}@localhost:27017/?authSource=admin`);
const lab=connection.getDB('bigdata_final');
if (!lab.getCollectionNames().includes('sensores_datos')) {
  lab.createCollection('sensores_datos',{validator:{$jsonSchema:{bsonType:'object',required:['timestamp','sensor_id','station','city','type','value','unit'],properties:{timestamp:{bsonType:'date'},value:{bsonType:['double','int','long','decimal']},sensor_id:{bsonType:'string'}}}}});
}
lab.sensores_datos.createIndex({sensor_id:1,timestamp:1},{unique:true});
lab.sensores_datos.createIndex({type:1,timestamp:1,city:1});
printjson({database:lab.getName(),collection:'sensores_datos',documents:lab.sensores_datos.countDocuments({})});
if (process.env.BIGDATA_EXPECTED_COUNT && lab.sensores_datos.countDocuments({}) !== Number(process.env.BIGDATA_EXPECTED_COUNT)) {
  throw new Error('Conteo distinto de la muestra esperada; revisar la colección antes de integrar.');
}
