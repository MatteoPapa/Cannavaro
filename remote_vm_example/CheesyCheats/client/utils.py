import grpc
import string
import random
from hashlib import sha256

p = 0x80000000000001cda6f403d8a752a4e7976173ebfcd2acf69a29f4bada1ca3178b56131c2c1f00cf7875a2e7c497b10fea66b26436e40b7b73952081319e26603810a558f871d6d256fddbec5933b77fa7d1d0d75267dcae1f24ea7cc57b3a30f8ea09310772440f016c13e08b56b1196a687d6a5e5de864068f3fd936a361c5

cc_api, cc_api_grpc = grpc.protos_and_services("cheesycheatsAPI.proto")
cc_manager, cc_manager_grpc = grpc.protos_and_services("cheesycheats.proto")
ROOT_CERTIFICATE = open("ca-cert.pem", "rb").read()

def create_client_channel(addr, auth_gateway=False):
    channel_credential = grpc.ssl_channel_credentials(ROOT_CERTIFICATE)

    if auth_gateway:
        call_credentials = grpc.metadata_call_credentials(auth_gateway, name = "auth gateway")
        credentials = grpc.composite_channel_credentials(channel_credential, call_credentials,)
    else:
        credentials = channel_credential
    channel = grpc.secure_channel(addr, credentials)    
    return channel

def user_login(stub, username, password):
    if isinstance(password, str):
        password = password.encode()
    g = pow(int(sha256(password).hexdigest(),16),2,p)
    a = random.randint((p-1)//2, p-2)
    g_a = pow(g,a,p)

    request = cc_manager.LoginStep1Request(username = username, g_a = hex(g_a)[2:])
    response = stub.LoginStep1(request)
    
    if not response.status:
        return ""
    
    g_b = int(response.g_b, 16)
    K = pow(g_b, a, p)
    request = cc_manager.LoginStep2Request(username = username, K = hex(K)[2:])
    response = stub.LoginStep2(request)

    if not response.status:
        return ""

    return response.session

def user_register(stub, username, password):
    request = cc_manager.RegistrationRequest(username = username, password = password)
    response = stub.Register(request)
    return response.status

def sell(stub, title, body, prefix=None, target=None):
    cheat = cc_manager.Cheat(title=title, body=body, prefix=prefix, target=target)
    req = cc_manager.SellCheatRequest(cheat=cheat)
    resp = stub.SellCheat(req)

    if not resp.status:
        return ""
    
    return resp.id

def list_own(stub):
    req = cc_manager.ListRequest()
    resp = stub.ListOwnCheats(req)

    if not resp.status:
        return []
    return resp.cheats

def run(stub, cheat_id, stdin=''):
    req = cc_api.RunRequest(id=cheat_id, STDIN=stdin)
    resp = stub.Run(req)
    return resp.STDOUT

def redeem(stub, cheat_id):
    req = cc_api.RedeemRequest(id=cheat_id)
    resp = stub.Redeem(req)
    return resp.cheat

def get_cheat_info(stub, cheat_id):
    info = cc_manager.GetCheatInfoRequest(cheat_id = cheat_id)
    resp = stub.GetCheatInfo(info)
    return resp

def buy(stub, cheat_id, unlocker):
    buy_req = cc_manager.BuyCheatRequest(cheat_id = cheat_id, preimage = unlocker)
    resp = stub.BuyCheat(buy_req)
    return resp

class TokenGateway(grpc.AuthMetadataPlugin):
    def __init__(self, token) -> None:
        self.token = token
        super().__init__()

    def __call__(self, context, callback):
        callback((('auth-token', self.token),), None)
    