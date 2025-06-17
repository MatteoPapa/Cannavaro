import grpc
import json
import vm
import logging

cc_pb2, cc_pb2_grpc = grpc.protos_and_services("cheesycheatsAPI.proto")


class Api(cc_pb2_grpc.DatabaseServicer):
    def __init__(self, db) -> None:
        self.db = db
        super().__init__()

    def Redeem(self, request, _, user):
        cheat_id = request.id
        user_cheat_key = 'user.' + user + '.cheats'

        if user_cheat_key in self.db:
            cheat_list = self.db['user.' + user + '.cheats']
        else:
            cheat_list = []
        if  cheat_id not in cheat_list:
            raise Exception('You do not own this cheat! Go buy it!')

        cheat_body = self.db['cheat.' + cheat_id + '.body']
        cheat_title = self.db['cheat.' + cheat_id + '.title']
        cheat = cc_pb2.Cheat(id=cheat_id, name=cheat_title, code=cheat_body)

        return cc_pb2.RedeemReply(status=True, cheat=cheat)

    def Run(self, request, _, user):
        cheat_id = request.id
        stdin = request.STDIN 
        if 'cheat.' + cheat_id + '.body' not in self.db:
            return cc_pb2.RunReply(status=False, STDOUT='')

        cheat_body = self.db['cheat.' + cheat_id + '.body']
        cheat = vm.CheesyVM(cheat_body)
        
        return cc_pb2.RunReply(status=True, STDOUT=cheat(stdin))

        




    