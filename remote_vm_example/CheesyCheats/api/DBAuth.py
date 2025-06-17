import os
import grpc
from grpc_interceptor import ServerInterceptor
import logging

class DBAuthInterceptor(ServerInterceptor):

    def __init__(self) -> None:
        self.SECRET = os.environ['DB_SECRET']
        super().__init__()
    
    def intercept(
        self,
        method,
        request,
        context,
        method_name
    ) :
        
        if method_name.split('/')[1] != 'cheesycheatsApi.Database':
            return method(request, context)

        metadata = context.invocation_metadata()

        if metadata is None or len(metadata) == 0:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("No auth token sent")
            raise Exception("No auth token sent", grpc.StatusCode.UNAUTHENTICATED)

        token = self.get_header(metadata, 'auth-token')

        if token != self.SECRET:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("You don't have access to this resource")
            raise Exception("You don't have access to this resource.", grpc.StatusCode.UNAUTHENTICATED)
        return method(request, context)
    
    def get_header(self, metadata, header_name):
        for m in metadata:
            if m[0] == header_name:
                return m[1]
        return ''
        

    