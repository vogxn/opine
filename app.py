import json
import logging

from flask import Flask, redirect, url_for,\
    session, request, render_template, abort, flash, g, jsonify
from flask_oauthlib.client import OAuth
from flask_cors import cross_origin
from marshmallow import ValidationError
from datetime import datetime
from peewee import OperationalError
from werkzeug.local import LocalProxy

from settings import DEBUG, SECRET_KEY
from models import database, Installation, Stats
from proxy import GithubCommentProxy
from forms import RegisterForm

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth(app)
proxy = GithubCommentProxy(oauth)


def get_db():
    db = getattr('_database', None)
    if db is None:
        try:
            database.connect()
            db = g._database = database
        except OperationalError as oex:
            dblog = logging.getLogger("opine.db")
            dblog.warn("database connect fails with %s" % oex)
    return db


@app.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


db = LocalProxy(get_db)


@app.route('/', methods=['GET'])
@cross_origin(supports_credentials=True, automatic_options=True)
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
@cross_origin(supports_credentials=True, automatic_options=True)
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
                app.logger.info("comment payload\n %s" % payload)
                if proxy.create(payload):
                    admin = Installation.get(Installation.ghid ==
                                             session.get('ghid'))
                    with database.transaction():
                        stat, created = Stats.get_or_create(
                            installation=admin,
                            defaults={'updated': datetime.now(), 'comments': 0}
                        )
                        if not created:
                            Stats.update(comments=Stats.comments + 1,
                                         updated=datetime.now())
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
