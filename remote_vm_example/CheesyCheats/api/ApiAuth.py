import os
import grpc
from grpc_interceptor import ServerInterceptor
import logging
from utils import *

class APIAuth(ServerInterceptor):
    def __init__(self, db) -> None:
        self.db = db 
        super().__init__()
    
    def intercept(
        self,
        method,
        request,
        context,
        method_name
    ) :
        package_name = method_name.split('/')[1]
        func_name = method_name.split('/')[2]

        if package_name != 'cheesycheatsApi.Api':
            return method(request, context)
        
        metadata = context.invocation_metadata()

        if metadata is None or len(metadata) == 0:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("No auth token sent")
            raise Exception("No auth token sent", grpc.StatusCode.UNAUTHENTICATED)
        
        token = self.get_header(metadata, 'auth-token')
        user = self.check_auth(token)

        if not user:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("You don't have access to this resource")
            raise Exception("You don't have access to this resource.", grpc.StatusCode.UNAUTHENTICATED)
        return method(request, context, user)
    
    def get_header(self, metadata, header_name):
        for m in metadata:
            if m[0] == header_name:
                return m[1]
        return ''
    
    def check_auth(self, token):        
        return verify_token(token)
        

    