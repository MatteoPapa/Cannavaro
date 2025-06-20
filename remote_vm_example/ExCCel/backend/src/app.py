import os
import time
import traceback
from functools import wraps

from cryptography.hazmat.primitives import hashes
from flask import Flask, request, session, g

from auth import generate_login_token, verify_login_token
from database import db
from models import User, Worksheet, Comment
from processor import EvaluationError, CompilingError, parse_formula, ParsingError, evaluate_formula
from sharing import generate_invite_token, verify_invite_token
from storage import get_cells, save_cells, Cell
from utils import make_json_response, make_error_response

app = Flask(__name__)
app.instance_path = os.getenv('INSTANCE_PATH', 'instance')
app.secret_key = os.getenv('FLASK_SECRET', os.urandom(16).hex().upper())
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///db.sqlite'

db.init_app(app)

with app.app_context():
    db.create_all()


def require_authentication(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return make_error_response(401, 'Not authenticated')

        user = db.session.execute(db.select(User).filter_by(id=session['user'])).scalar_one_or_none()
        if user is None:
            session.pop('user', None)
            return make_error_response(401, 'Not authenticated')

        g.user = user
        return f(*args, **kwargs)

    return wrapper


@app.route('/api/user', methods=['GET'])
def get_user():
    if 'user' not in session:
        return make_json_response({'logged': False})

    user = db.session.execute(db.select(User).filter_by(id=session['user'])).scalar_one_or_none()
    if user is None:
        session.pop('user', None)
        return make_json_response({'logged': False})

    return make_json_response({'logged': True, 'id': user.id})


@app.route('/api/register', methods=['POST'])
def register():
    username, password = request.json.get('username'), request.json.get('password')
    if not username or not password:
        return make_error_response(400, 'Missing username or password')

    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    if user is not None:
        return make_error_response(409, 'User already exists')

    user = User(
        username=username,
        password=password,
    )

    db.session.add(user)
    db.session.commit()

    return make_json_response({})


@app.route('/api/login/first', methods=['POST'])
def login_first():
    username = request.json.get('username')
    if not username:
        return make_error_response(400, 'Missing username')

    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    if user is None:
        return make_error_response(401, 'Wrong username')

    timestamp = int(time.time() * 1000)
    server_nonce, server_token = generate_login_token(user.password, timestamp)
    session['server_nonce'] = server_nonce.hex()
    session['timestamp'] = timestamp
    session['username'] = username

    return make_json_response({'token': server_token.hex(), 'timestamp': timestamp})


@app.route('/api/login/second', methods=['POST'])
def login_second():
    server_nonce = session.get('server_nonce')
    if not server_nonce:
        session.clear()
        return make_error_response(400, 'Invalid session')

    client_token = request.json.get('token')
    if not client_token:
        return make_error_response(400, 'Missing token')

    session['client_token'] = client_token
    return make_json_response({'nonce': server_nonce})


@app.route('/api/login/third', methods=['POST'])
def login_third():
    username, timestamp, server_nonce, client_token = (session.get('username'), session.get('timestamp'),
                                                       session.get('server_nonce'), session.get('client_token'))
    if not username or not timestamp or not server_nonce or not client_token:
        session.clear()
        return make_error_response(400, 'Invalid session')

    client_nonce = request.json.get('nonce')
    if not client_nonce:
        return make_error_response(400, 'Missing nonce')

    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    if user is None:
        return make_error_response(401, 'Invalid username')

    if (not verify_login_token(user.password, timestamp, bytes.fromhex(client_token), bytes.fromhex(client_nonce))
            or server_nonce == client_nonce):
        return make_error_response(401, 'Client verification failed')

    session.clear()
    session['user'] = user.id
    return make_json_response({'id': user.id})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return make_json_response({})


@app.route('/api/worksheets', methods=['GET'])
@require_authentication
def get_worksheets():
    return make_json_response([item.as_light_dict() for item in g.user.worksheets + g.user.guest_worksheets])


def process_formulas(worksheet_id: str, cells: list[Cell], timestamp: str):
    for cell in cells:
        try:
            formula = parse_formula(cells, cell.content)
            if formula is None:
                continue
        except ParsingError:
            traceback.print_exc()
            cell.evaluated = b'#PARSE?'  # 🤌🤌🤌
            continue

        try:
            formula.compile()
        except CompilingError:
            traceback.print_exc()
            cell.evaluated = b'#COMPILE?'  # 🤌🤌🤌
            continue

        try:
            cell.evaluated = evaluate_formula(worksheet_id, formula, timestamp)
        except EvaluationError:
            traceback.print_exc()
            cell.evaluated = b'#EVALUATE?'  # 🤌🤌🤌
            continue


@app.route('/api/worksheets', methods=['POST'])
@require_authentication
def create_worksheet():
    title = request.json.get('title')
    if not title:
        return make_error_response(400, 'Missing title')

    sharable = request.json.get('sharable')
    if sharable is None or not isinstance(sharable, bool):
        return make_error_response(400, 'Missing sharable')

    worksheet_private_id = os.urandom(128)
    digest = hashes.Hash(hashes.MD5())
    digest.update(worksheet_private_id)
    worksheet_public_id = digest.finalize()

    worksheet = Worksheet(
        public_id=worksheet_public_id.hex(),
        private_id=worksheet_private_id.hex(),
        sharable=sharable,
        title=title,
        owner=g.user
    )

    try:
        save_cells(worksheet_public_id.hex(), [])

        db.session.add(worksheet)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return make_json_response(worksheet.as_light_dict())


@app.route('/api/worksheet/<worksheet_id>', methods=['GET'])
@require_authentication
def get_worksheet(worksheet_id: str):
    worksheet = db.session.execute(db.select(Worksheet).filter_by(public_id=worksheet_id)).scalar_one_or_none()
    if worksheet is None:
        return make_error_response(404, 'No such worksheet')
    elif worksheet.owner != g.user and g.user not in worksheet.guests:
        return make_error_response(403, 'No permission to view this worksheet')

    cells = get_cells(worksheet.public_id)

    process_formulas(worksheet.public_id, cells, request.args.get('timestamp', ''))

    return make_json_response(worksheet.as_dict(cells))


@app.route('/api/worksheet/<worksheet_id>/invite/<token>', methods=['POST'])
@require_authentication
def invite_worksheet(worksheet_id: str, token: str):
    worksheet = db.session.execute(db.select(Worksheet).filter_by(public_id=worksheet_id)).scalar_one_or_none()
    if worksheet is None:
        return make_error_response(404, 'No such worksheet')
    elif worksheet.owner == g.user:
        return make_json_response({})
    elif not worksheet.sharable:
        return make_error_response(400, 'Worksheet cannot be shared')

    if not verify_invite_token(worksheet, token):
        return make_error_response(403, 'Invalid worksheet invite token')

    if g.user not in worksheet.guests:
        worksheet.guests.append(g.user)

    db.session.add(worksheet)
    db.session.commit()

    return make_json_response({})


@app.route('/api/worksheet/<worksheet_id>/share', methods=['POST'])
@require_authentication
def share_worksheet(worksheet_id: str):
    worksheet = db.session.execute(db.select(Worksheet).filter_by(public_id=worksheet_id)).scalar_one_or_none()
    if worksheet is None:
        return make_error_response(404, 'No such worksheet')
    elif worksheet.owner != g.user:
        return make_error_response(403, 'No permission to share this worksheet')
    elif not worksheet.sharable:
        return make_error_response(400, 'Worksheet cannot be shared')

    token = generate_invite_token(worksheet)

    return make_json_response({
        'token': token,
    })


@app.route('/api/worksheet/<worksheet_id>', methods=['POST'])
@require_authentication
def save_worksheet(worksheet_id: str):
    if 'cells' not in request.json:
        return make_error_response(400, 'Missing cells')

    worksheet = db.session.execute(db.select(Worksheet).filter_by(public_id=worksheet_id)).scalar_one_or_none()
    if worksheet is None:
        return make_error_response(404, 'No such worksheet')
    elif worksheet.owner != g.user:
        return make_error_response(403, 'No permission to edit this worksheet')

    json_cells = request.json['cells']
    if not isinstance(json_cells, list):
        return make_error_response(400, 'Invalid cells')

    cells = []
    for json_cell in json_cells:
        if 'x' not in json_cell or 'y' not in json_cell or 'content' not in json_cell:
            return make_error_response(400, 'Invalid cell')

        x, y, content = json_cell['x'], json_cell['y'], json_cell['content']
        if not isinstance(x, int) or not isinstance(y, int) or not isinstance(content, str):
            return make_error_response(400, 'Invalid cell')

        content = bytes.fromhex(content)
        if x < 0 or x > 63 or y < 0 or y > 63 or len(content) > 64:
            return make_error_response(400, 'Invalid cell')

        if Cell.contains(cells, x, y):
            return make_error_response(400, 'Duplicate cells')

        cells.append(Cell(x, y, content, None))

    save_cells(worksheet.public_id, cells)

    process_formulas(worksheet.public_id, cells, request.args.get('timestamp', ''))

    return make_json_response(worksheet.as_dict(cells))


@app.route('/api/worksheet/<worksheet_id>/comments', methods=['POST'])
@require_authentication
def create_comment(worksheet_id: str):
    worksheet = db.session.execute(db.select(Worksheet).filter_by(public_id=worksheet_id)).scalar_one_or_none()
    if worksheet is None:
        return make_error_response(404, 'No such worksheet')
    elif worksheet.owner != g.user and g.user not in worksheet.guests:
        return make_error_response(403, 'No permission to comment on this worksheet')

    cell_x, cell_y, content = request.json.get('x'), request.json.get('y'), request.json.get('content')
    if cell_x is None or cell_y is None or not content:
        return make_error_response(400, 'Missing cell or content')
    elif not isinstance(cell_x, int) or not isinstance(cell_y, int) or cell_x < 0 or cell_y < 0:
        return make_error_response(400, 'Invalid cell')
    elif not isinstance(content, str) or len(content) > 64:
        return make_error_response(400, 'Invalid content')

    comment = Comment(
        cell_x=cell_x,
        cell_y=cell_y,
        created_at=int(time.time()),
        content=content,
        worksheet=worksheet,
        owner=g.user,
    )

    db.session.add(comment)
    db.session.commit()

    return make_json_response({'id': comment.id})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
