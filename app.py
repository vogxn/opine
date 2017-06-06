import json
import logging

from flask import Flask, redirect, url_for,\
    session, request, render_template, abort, jsonify, flash, g
from flask_oauthlib.client import OAuth
from flask_cors import CORS
from werkzeug import security
from marshmallow import ValidationError
from datetime import datetime

from settings import API_URL, CLIENT_ID, CLIENT_SECRET, DEBUG, SECRET_KEY
from models import database, Installation
from comment import AdminSchema
from proxy import GithubCommentProxy
from forms import RegisterForm

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
            return jsonify(proxy.get(title='slug-url-first-comment'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET'])
def login():
    data = {"login": "vogxn", "repo": "vogxn.github.io"}
    if data:  # request.get_json():
        adminschema = AdminSchema()
        admin = adminschema.load(data).data
        proxy.connect(admin.login, admin.repo, github)
        assert proxy.valid
        return github.authorize(callback=url_for('authorized', _external=True))
    else:
        abort(422)


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    # display register form
    rform = RegisterForm()
    if request.method == "POST" and rform.validate_on_submit():
        with database.transaction():
            Installation.create(ghid=session.get('ghid'),
                                owner=rform.login.data,
                                repo=rform.repo.data,
                                origin=rform.origin.data,
                                active=True,
                                created=datetime.now(),
                                updated=datetime.now())
        flash("Successfully Registered!")
        return redirect(url_for('index'))
    else:
        installation_id = request.args.get('installation_id')
        session['ghid'] = installation_id
        return render_template('register.html', form=rform)


@app.route('/comment', methods=['GET'])
def comment():
    if 'gh_token' not in session:
        return redirect(url_for('login'))
    else:
        try:
            payload = request.get_json()
            proxy.create(payload)
            return redirect(url_for('index'))
        except json.JSONDecodeError:
            abort(422)
        except ValidationError as err:
            return err.messages


@github.tokengetter
def get_github_oauth_token():
    return session.get('gh_token')


@app.before_request
def before_request():
    g.db = database
    g.db.connect()


@app.after_request
def after_request(response):
    g.db.close()
    return response


if __name__ == '__main__':
    app.run(port=8080)
