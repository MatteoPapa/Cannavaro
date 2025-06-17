from concurrent import futures
import contextlib
import logging
import grpc
import utils
import os
from Auth import Auth
from db import *
import uuid
from hashlib import sha256
import random
import json
from utils import *

cc_pb2, cc_pb2_grpc = grpc.protos_and_services("cheesycheats.proto")
DB_ADDR = os.environ.get('API_HOST', "cheats_api:5555")
SERVER_CERTIFICATE = open("server-cert.pem", "rb").read()
SERVER_CERTIFICATE_KEY = open("server-key.pem", "rb").read()

class Manager(cc_pb2_grpc.ManagerServicer):
    def __init__(self) -> None:
        self.db = get_db(DB_ADDR)
        super().__init__()

    def Register(self, request, _): 
        try:
            assert 'user.'+request.username not in self.db
            self.db['user.' + request.username] = request.password
            self.db['loginkeys.' + request.username] = []
            return cc_pb2.RegistrationReply(status = True)
            
        except:
            return cc_pb2.RegistrationReply(status = False)
    
    def LoginStep1(self, request, _):
        try:
            assert 'user.' + request.username in self.db
            user_password = self.db['user.' + request.username].encode()
            h = sha256(user_password).hexdigest()
            g = pow(int(h, 16), 2, utils.p)
            b = random.randint((utils.p-1)//2, utils.p-1)
            g_b = pow(g, b, utils.p)
            K = pow(int(request.g_a, 16), b, utils.p)
            loginkeys = self.db['loginkeys.' + request.username]
            loginkeys.append(hex(K)[2:])
            self.db['loginkeys.' + request.username] = loginkeys
            return cc_pb2.LoginStep1Reply(status = True, g_b = hex(g_b)[2:])
            
        except:
            return cc_pb2.LoginStep1Reply(status = False)

    def LoginStep2(self, request, _):
        try:
            assert 'user.' + request.username in self.db
            if request.K in self.db['loginkeys.' + request.username]:
                session = os.urandom(6).hex()
                loginkeys = self.db['loginkeys.' + request.username]
                loginkeys.remove(request.K)
                self.db['loginkeys.' + request.username] = loginkeys

                data = request.username 
                session = sign_token(data)
                
                return cc_pb2.LoginStep2Reply(status = True, session = session)
            
        except:
            return cc_pb2.LoginStep2Reply(status = False)

    def SellCheat(self, request, context, user = None):
        try:
            cheat = request.cheat
            cheat_id = str(uuid.uuid4())
            
            self.db['cheat.' + cheat_id + '.title' ] = cheat.title
            self.db['cheat.' + cheat_id + '.body'] = cheat.body
            self.db['cheat.' + cheat_id + '.prefix'] = cheat.prefix
            self.db['cheat.' + cheat_id + '.target'] = cheat.target
            self.db['cheat.' + cheat_id + '.preimages'] = []

            try:
                owned_cheats = self.db['user.' + user + '.cheats' ]
            except:
                owned_cheats = []

            owned_cheats.append(cheat_id)
            self.db['user.' + user +'.cheats' ] = owned_cheats
            
            return cc_pb2.SellCheatReply(id = cheat_id, status = True)
        except:
            return cc_pb2.SellCheatReply(status = False)
    
    def GetCheatInfo(self, request, _, user = None):
        try:
            cheat_id = request.cheat_id
            
            prefix = self.db['cheat.' + cheat_id + '.prefix']
            target = self.db['cheat.' + cheat_id + '.target']
            title = self.db['cheat.' + cheat_id + '.title']
            
            preimages = self.db['cheat.' + cheat_id + '.preimages']

            if 'user.' + user + '.cheats' in self.db and cheat_id in self.db['user.' + user + '.cheats']:
                response = cc_pb2.GetCheatInfoReply(status = True, title = title)
                for pr in preimages:
                    response.preimages.append(pr)
                return response

            if not prefix or not target:
                return cc_pb2.GetCheatInfoReply(status = True)
            return cc_pb2.GetCheatInfoReply(status = True, prefix = prefix, target = target)

        except Exception as e:
            logging.info(e)
            return cc_pb2.GetCheatInfoReply(status = False)

    def BuyCheat(self, request, _, user = None):
        try:
            cheat_id = request.cheat_id
            
            prefix = self.db['cheat.' + cheat_id + '.prefix']
            target = self.db['cheat.' + cheat_id + '.target']

            if not prefix or not target:
                return cc_pb2.BuyCheatReply(status = False)

            if utils.verify_pow(prefix, target, request.preimage):
                preimages = self.db['cheat.' + cheat_id + '.preimages']
                preimages.append(request.preimage)
                self.db['cheat.' + cheat_id + '.preimages'] = preimages
                
                try:
                    owned_cheats = self.db['user.' + user + '.cheats' ]
                except:
                    owned_cheats = []

                owned_cheats.append(cheat_id)
                self.db['user.' + user +'.cheats'] = owned_cheats
                return cc_pb2.BuyCheatReply(status = True)
            return cc_pb2.BuyCheatReply(status = False)
        except:
            return cc_pb2.BuyCheatReply(status = False)

    def ListOwnCheats(self, request, _, user = None):
        try:
            try:
                cheats = self.db['user.' + user + '.cheats']
            except KeyError:
                cheats = []

            response = cc_pb2.CheatListReply(status = True)
            
            for cheat in cheats:
                try:
                    cheat_title = self.db['cheat.' + cheat + '.title']
                except KeyError:
                    continue
                tmp_cheat = cc_pb2.Cheat(id = cheat, title = cheat_title)
                response.cheats.append(tmp_cheat)
            return response
        except:
            return cc_pb2.CheatListReply(status = False)

@contextlib.contextmanager
def run_server(port):
    server = grpc.server(futures.ThreadPoolExecutor(), interceptors=(Auth(get_db(DB_ADDR)), ))

    cc_pb2_grpc.add_ManagerServicer_to_server(Manager(), server)
    server_credentials = grpc.ssl_server_credentials(((SERVER_CERTIFICATE_KEY, SERVER_CERTIFICATE,),))
    port = server.add_secure_port(f"0.0.0.0:{port}", server_credentials)

    server.start()
    try:
        yield server, port
    finally:
        server.stop(0)

def main():
    port = 5000

    with run_server(port) as (server, port):
        logging.info("Server is listening at port :%d", port)
        server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    main()
