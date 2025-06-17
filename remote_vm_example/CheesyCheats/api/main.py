from concurrent import futures
import contextlib
import logging
import grpc
import os
import sqlitedict
import json
from DBAuth import *
from ApiAuth import APIAuth
from Database import Database, db
from Api import Api

cc_pb2, cc_pb2_grpc = grpc.protos_and_services("cheesycheatsAPI.proto")

SERVER_CERTIFICATE = open("server-cert.pem", "rb").read()
SERVER_CERTIFICATE_KEY = open("server-key.pem", "rb").read()

@contextlib.contextmanager
def run_server(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), interceptors=(DBAuthInterceptor(),APIAuth(db)))

    cc_pb2_grpc.add_DatabaseServicer_to_server(Database(db), server)
    cc_pb2_grpc.add_ApiServicer_to_server(Api(db), server)
    server_credentials = grpc.ssl_server_credentials(((SERVER_CERTIFICATE_KEY, SERVER_CERTIFICATE,),))
    server_credentials = grpc.ssl_server_credentials(((SERVER_CERTIFICATE_KEY, SERVER_CERTIFICATE,),))
    port = server.add_secure_port(f"0.0.0.0:{port}", server_credentials)
    server.start()
    try:
        yield server, port
    finally:
        server.stop(0)

def main():
    port = 5555

    with run_server(port) as (server, port):
        logging.info("Server is listening at port :%d", port)
        server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    main()