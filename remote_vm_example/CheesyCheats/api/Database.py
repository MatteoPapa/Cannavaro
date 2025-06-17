import grpc
from db import Db
import json
import logging

cc_pb2, cc_pb2_grpc = grpc.protos_and_services("cheesycheatsAPI.proto")

db = Db('/opt/store.db',  autocommit=True,
                        encode=json.dumps, decode=json.loads)

class Database(cc_pb2_grpc.DatabaseServicer):
    def __init__(self, db) -> None:
        self.db = db
        super().__init__()

    def Put(self, request, _):
        key = request.id
        result = cc_pb2.Result()
       
        if key in self.db:
            result.status_code = 403
            result.status = 'Cannot overwrite key. Use update'
        else:
            result.status_code = 200
            result.status = 'ok'
            if len(request.entry.values) > 0 and not request.entry.value:
                value = []
            if len(request.entry.values) > 0:
                value = list(request.entry.values)
            else:
                value = request.entry.value
            self.db[key] = value
        return result

    def Get(self, request, _):
        key = request.id
        result = cc_pb2.Result()

        if key not in self.db:
            result.status_code = 404
            result.status = 'Key not found'
        else:
            result.status_code = 200
            result.status = 'ok'
            result.entry.id = key
            value = self.db[key]
            
            if type(value) is str:
                result.entry.value = value
            elif type(value) is list:
                result.entry.values.extend(value)
            else:
                logging.info(value)
                result.entry.value = str(value)
            
        return result

    def Delete(self, request, _):
        key = request.id
        result = cc_pb2.Result()

        if key not in self.db:
            result.status_code = 404
            result.status = 'Key not found'
        else:
            result.status_code = 200
            result.status = 'ok'
            result.entry.id = key
            result.entry.value = self.db[key]
            del self.db[key]
        
        return result

    def Update(self, request, _):
        key = request.id
        result = cc_pb2.Result()

        if key not in self.db:
            result.status_code = 404
            result.status = 'Key not found'
        else:
            result.status_code = 200
            result.status = 'ok'
            old_value = self.db[key]

            
            if len(request.entry.values) > 0:
                value = list(request.entry.values)
            else:
                value = request.entry.value

            if old_value == '':
                old_value = []

            if value == '':
                value = []

            if type(old_value) is type(value):
                self.db[key] = value
            else:
                raise Exception('Cannot Change value type')
        
        return result