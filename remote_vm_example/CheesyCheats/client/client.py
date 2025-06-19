from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich import print
from rich.panel import Panel
from utils import *
import sys

intro = open("intro.txt").read()
target = None
cc_pb2, cc_pb2_grpc = grpc.protos_and_services("cheesycheats.proto")
ROOT_CERTIFICATE = open("ca-cert.pem", "rb").read()
import os

# os.environ["GRPC_VERBOSITY"] = "debug"
# os.environ["GRPC_TRACE"] = "all"


def exit_service(*args):
    raise SystemExit

def register(stub, channel, console, session):
    username = input("username: ")
    password = input("password: ")

    resp = user_register(stub, username, password)

    if resp:
        print("Account registered!")
    else:
        print("Registration failed!")
        
    return None

def login(stub, channel, console, session):
    username = input("username: ")
    password = input("password: ")

    try:
        session = user_login(stub, username, password)
        assert len(session) > 0
    except:
        print("Login Error")
        return None

    return session

def buy_cheat(stub, channel, console, session):
    print(stub)
    cheat_id = input("cheat id: ")
    info = get_cheat_info(stub, cheat_id)
    print("[+] Cheat Info:")
    print(f"  Status:  {info.status}")
    print(f"  Title:   {info.title}" if info.HasField("title") else "  Title:   [not available]")
    print(f"  Prefix:  {info.prefix}" if info.HasField("prefix") else "  Prefix:  [not available]")
    print(f"  Target:  {info.target}" if info.HasField("target") else "  Target:  [not available]")

    if info.preimages:
        print("  Preimages:")
        for pre in info.preimages:
            print(f"    - {pre}")
            
    if not info.status:
        return session
    
    print(f"To buy this cheat, provide a string starting with {info.prefix} such that its md5 starts with {info.target}.")

    ans = input("answer: ")
    
    resp = buy(stub, cheat_id, str(ans))

    if not resp or not resp.status:
        print("Something went wrong!")
    else:
        print("Success! You can find the cheat in your cheats.")

    return session

def redeem_cheat(stub, channel, console, session):
    cheat_id = input("cheat id: ")
    channel_api = create_client_channel(f'{target}:5555', TokenGateway(session))
    stub_api = cc_api_grpc.ApiStub(channel_api)
    print(redeem(stub_api, cheat_id).code)
    return session

def sell_cheat(stub, channel, console, session):
    title = input("cheat title: ")
    code = input("cheat code: ")
    prefix = input("hash prefix: ")
    target_hash = input("hash target: ")
    cheat_id = sell(stub, title, code, prefix, target_hash)

    if cheat_id:
        print(f"Here's your cheat id: {cheat_id}")
    else:
        print("Something went wrong")

    return session

def list_cheats(stub, channel, console, session):
    cheat_ids = list_own(stub)

    if len(cheat_ids)>0:
        table = Table(title="Your cheats")

        table.add_column("#", justify="right")
        table.add_column("Id")
        table.add_column("Title")

        for i, cheat in enumerate(cheat_ids):
            table.add_row(str(i), cheat.id, cheat.title)
        
        console.print(table)

        return session

def demo(stub, channel, console, session):
    cheat_id = input("cheat id: ")
    stdin = input("your input to the cheat: ")

    channel_api = create_client_channel(f'{target}:5555', TokenGateway(session))
    stub_api = cc_api_grpc.ApiStub(channel_api)
    try:
        stdout = run(stub_api, cheat_id, stdin)
        print(f"Here's your output: {stdout}")
    except:
        print("Something went wrong")

    return session

def logout(stub, channel, console, session):
    return None

def main():
    global target
    if len(sys.argv) < 2:
        print("usage: ./client.py <target>")
        exit()
        
    target = sys.argv[1]
    port = 5000
    session = None
    console = Console(width = 100)
    print(Panel.fit("Welcome to [yellow]CheesyCheats!"))
    print(intro)

    menu_no_login = (["register", "login", "exit"], [register, login, exit_service])
    menu_login = (["buy cheat", "sell cheat", "list my cheats", "redeem cheat", "try cheat", "logout", "exit"], [buy_cheat, sell_cheat, list_cheats, redeem_cheat, demo, logout, exit_service])
    
    while True:
        try:
            if session is None:
                channel = create_client_channel(f"{target}:{port}")
                stub = cc_manager_grpc.ManagerStub(channel)
                options = menu_no_login
            else:
                channel = create_client_channel(f"{target}:{port}", TokenGateway(session))
                stub = cc_manager_grpc.ManagerStub(channel)
                options = menu_login
            cmd = Prompt.ask("What do you want to do?", choices = options[0])
            session = options[1][options[0].index(cmd)](stub, channel, console, session)
        except:
            exit()

if __name__ == "__main__":
    main()
