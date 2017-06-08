import json
import logging

from flask import Flask, redirect, url_for,\
    session, request, render_template, abort, flash, g, jsonify
from flask_oauthlib.client import OAuth
from flask_cors import CORS
from marshmallow import ValidationError
from datetime import datetime

from settings import DEBUG, SECRET_KEY
from models import database, Installation
from proxy import GithubCommentProxy
from forms import RegisterForm

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
cors = CORS(app)
oauth = OAuth(app)
proxy = GithubCommentProxy(oauth)


@app.route('/', methods=['GET'])
def index():
    if 'ghid' not in session:
        if 'ghid' in request.args:
            session['ghid'] = request.args.get('ghid')
        else:
            # FIXME: ask user to pass ghid or raise misconfiguration error
            abort(422)
    try:
        admin = Installation.get(Installation.ghid == session.get('ghid'))
        if admin.active:
            proxy.configure(admin.owner, admin.repo)
            return render_template('index.html')
        else:
            # FIXME: inactive installation
            abort(422)
    except Installation.DoesNotExist:
        # FIXME: invalid installation
        abort(422)


# FIXME: to be made POST with installation data sent in garbled text
@app.route('/login', methods=['GET'])
def login():
    return proxy.client.authorize(callback=url_for('authorize', _external=True))


@app.route('/logout')
def logout():
    session.pop('gh_token', None)
    return redirect(url_for('index'))


@app.route('/authorize')
def authorize():
    resp = proxy.client.authorized_response()
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


@app.route('/deregister', methods=['POST'])
def deregister():
    """ Uninstallation hook to inactivate the installation """
    raise NotImplementedError


@app.route('/comment', methods=['GET', 'POST'])
def comment():
    if request.method == "GET":
        # FIXME: how will /comment block until proxy is valid?
        return jsonify(proxy.get(title=request.args.get('title')))
    elif request.method == "POST":
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


@proxy.client.tokengetter
def get_github_token(token=None):
    if 'gh_token' in session:
        return session.get('gh_token')
    return None


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
