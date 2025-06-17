import grpc
import logging
import os

cc_pb_db, cc_pb_db_grpc = grpc.protos_and_services("cheesycheatsAPI.proto")
ROOT_CERTIFICATE = open("ca-cert.pem", "rb").read()

logging.basicConfig(level = logging.INFO)

class AuthGateway(grpc.AuthMetadataPlugin):
    def __init__(self) -> None:
        self.SECRET = os.environ.get('DB_SECRET', '')
        super().__init__()

    def __call__(self, context, callback):
        signature = self.SECRET 
        callback((("auth-token", signature),), None)

class Db(dict):

    def __init__(self, addr):
        call_credentials = grpc.metadata_call_credentials(AuthGateway(), name = "auth gateway")
        channel_credential = grpc.ssl_channel_credentials(ROOT_CERTIFICATE)
        composite_credentials = grpc.composite_channel_credentials(channel_credential, call_credentials,)
        self.channel = grpc.secure_channel(addr, composite_credentials)
        self.stub = cc_pb_db_grpc.DatabaseStub(self.channel)
        super().__init__()

    def __setitem__(self, key, item):
        
        if type(item) is list:
            entry = cc_pb_db.Entry(id=key, values=item)
        else:
            entry = cc_pb_db.Entry(id=key, value=item)

        req = cc_pb_db.PutRequest(id=key, entry=entry)
        response = self.stub.Put(req)

        if response.status_code == 403:
            req = cc_pb_db.UpdateRequest(id=key, entry=entry)
            try:
                response = self.stub.Update(req)
            except:
                raise Exception('Cannot change value type')
        

    def __getitem__(self, key):
        req = cc_pb_db.GetRequest(id=key)
        response = self.stub.Get(req)

        if response.status_code != 200:
            raise KeyError(f'Key {key} not found.')

        entries_n = len (response.entry.values)

        if entries_n == 0 and not response.entry.value:
            return []
        
        if entries_n > 0:
            return list(response.entry.values)
        return response.entry.value

    def __repr__(self):
        return '<Remote GRPC Dictionary>'

    def __delitem__(self, key):
        req = cc_pb_db.DeleteRequest(id=key)
        response = self.stub.Delete(req)
        if response.status_code != 200:
            raise KeyError

    def __contains__(self, k):
        
        try:
            self.__getitem__(k)
        except KeyError:
            return False
        return True
    
db = None
def get_db(addr):
    global db
    if db is None:
        db = Db(addr)
    return db