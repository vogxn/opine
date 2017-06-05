import json
import logging

from flask import Flask, redirect, url_for, session, request
from flask_oauthlib.client import OAuth
from flask_cors import CORS
from werkzeug import security
from marshmallow import ValidationError

from settings import API_URL, CLIENT_ID, CLIENT_SECRET, DEBUG, SECRET_KEY
from comment import AdminSchema
from proxy import GithubCommentProxy

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
cors = CORS(app)
oauth = OAuth(app)


proxy = GithubCommentProxy()
github = oauth.remote_app(
    'github',
    consumer_key=CLIENT_ID,
    consumer_secret=CLIENT_SECRET,
    request_token_params={
        'state': lambda: security.gen_salt(10)
    },
    base_url=API_URL,
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)


def change_app_header(uri, headers, body):
    headers["Accept"] = "application/vnd.github.machine-man-preview+json"
    return uri, headers, body

github.pre_request = change_app_header


@app.route('/', methods=['GET'])
def index():
    if 'gh_token' in session:
        if proxy.valid:
            return proxy.get()
    return redirect(url_for('login'))


@app.route('/login', methods=['POST'])
def login():
    adminschema = AdminSchema()
    admin = adminschema.load(request.get_json()).data
    proxy.connect(admin.login, admin.repo, github)
    assert proxy.valid
    return github.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('gh_token', None)
    return redirect(url_for('index'))


@app.route('/authorize')
def authorized():
    resp = github.authorized_response()
    if resp is None or resp.get('access_token') is None:
        return 'Access denied: reason=%s error=%s resp=%s' % (
            request.args['error'],
            request.args['error_description'],
            resp
        )
    session['gh_token'] = (resp['access_token'], '')
    return redirect(url_for('index'))


@app.route('/comment', methods=['POST'])
def comment():
    if 'gh_token' not in session:
        return redirect(url_for('login'))
    else:
        try:
            payload = request.get_json()
            proxy.create(payload)
            return redirect(url_for('index'))
        except json.JSONDecodeError:
            return 422
        except ValidationError as err:
            return err.messages


@github.tokengetter
def get_github_oauth_token():
    return session.get('gh_token')


# @app.before_request
# def before_request():
#     g.db = database
#     g.db.connect()
#
#
# @app.after_request
# def after_request(response):
#     g.db.close()
#     return response
#

if __name__ == '__main__':
    app.run(port=8080)
