import json
import logging

from flask import Flask, redirect, url_for,\
    session, request, render_template, abort, flash, g, jsonify
from flask_oauthlib.client import OAuth
from flask_cors import cross_origin
from marshmallow import ValidationError
from datetime import datetime
from peewee import OperationalError, IntegrityError
from werkzeug.local import LocalProxy
from functools import wraps

from settings import DEBUG, SECRET_KEY
from models import DB, Installation, Stats
from proxy import GithubCommentProxy
from forms import RegisterForm

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth(app)
proxy = GithubCommentProxy(oauth)


def override_origin(routing_func):
    """ This decorator is used to override the default origin header set by
    flask-cors. The default is wildcard (*). For each request we set the
    header to the origin as identified by the installation during registration
    """
    @wraps(routing_func)
    def wrapper(*args, **kwargs):
        resp = routing_func(*args, **kwargs)
        if 'ghid' not in session:
            ghid = request.args.get('ghid')
        else:
            ghid = session.get('ghid')
        if ghid is not None:
            install = Installation.get(Installation.ghid == ghid)
            resp.headers["Access-Control-Allow-Origin"] = install.origin
        # return the regular wildcard response if 'ghid' is not supplied
        return resp
    return wrapper


def get_db():
    """ get_db() returns the db connection in the ApplicationContext """
    db = getattr(g, '_database', None)
    if db is None:
        try:
            DB.connect()
            db = g._database = DB
        except OperationalError as oex:
            dblog = logging.getLogger("opine.db")
            dblog.warning("database connect fails with %s" % oex)
    return db


@app.teardown_appcontext
def teardown_db(exception):
    """ teardown_db() will cleanup the database connection for each request/app context """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

db = LocalProxy(get_db)  # werkzeug proxied local for database connectivity


@app.route('/', methods=['GET'])
@override_origin
@cross_origin(supports_credentials=True, automatic_options=True)
def index():
    if 'ghid' not in session:
        if 'ghid' in request.args:
            session['ghid'] = request.args.get('ghid')
        else:
            # FIXME: ask user to pass ghid or raise misconfiguration error
            # TODO: needs errorhandler pages
            abort(422)
    try:
        admin = Installation.get(Installation.ghid == session.get('ghid'))
        if admin.active:
            proxy.configure(admin.owner, admin.repo)
            return render_template('index.html')
        else:
            # FIXME: inactive installation
            # TODO: needs errorhandler page for inactive installation
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
    """ oauth authorize """
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
    """ registration process after a successful app install """
    rform = RegisterForm()
    if request.method == "POST" and rform.validate_on_submit():
        try:
            with DB.atomic() as txn:
                Installation.create(ghid=session.get('ghid'),
                                    owner=rform.login.data,
                                    repo=rform.repo.data,
                                    origin=rform.origin.data,
                                    active=True,
                                    created=datetime.now(),
                                    updated=datetime.now())
        except IntegrityError:
            flash("Failed registration!")
            abort(422)
        else:
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
@override_origin
@cross_origin(supports_credentials=True, automatic_options=True)
def comment():
    """ /comment retrieves or posts comments from/to github issues """
    if request.method == "GET":
        return jsonify(proxy.get(title=request.args.get('title')))
    elif request.method == "POST":
        if 'gh_token' not in session:
            return redirect(url_for('login'))
        else:
            try:
                payload = request.get_json()
                app.logger.debug("comment payload\n %s" % payload)
                if proxy.create(payload):
                    app.logger.info("comment posted successfully")
                    admin = Installation.get(Installation.ghid ==
                                             session.get('ghid'))
                    record_stats(admin)
                return redirect(url_for('index'))
            except json.JSONDecodeError:
                abort(422)
            except ValidationError as err:
                return err.messages


def record_stats(install):
    """ increment counters for comments in the installation """
    with DB.atomic() as txn:
        stat, created = Stats.get_or_create(
            installation=install,
            defaults={'updated': datetime.now(), 'comments': 0}
        )
        if not created:
            stat.updated = datetime.now()
            stat.comments += 1
            with DB.atomic() as innertxn:
                stat.save()


@proxy.client.tokengetter
def get_github_token(token=None):
    """ github token getter """
    if 'gh_token' in session:
        return session.get('gh_token')
    return None
