from flask import Flask, redirect, url_for, session, request, jsonify, g
from flask_oauthlib.client import OAuth
from werkzeug import security
from urllib.parse import urlparse
from slugify import slugify
from marshmallow import ValidationError
from comment import CommentSchema
from models import Installation, database
from settings import *
import json

app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth(app)


github = oauth.remote_app(
    'github',
    consumer_key=CLIENT_ID,
    consumer_secret=CLIENT_SECRET,
    request_token_params={
        'state': lambda: security.gen_salt(10)
    },
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)


def change_app_header(uri, headers, body):
    headers["Accept"] = "application/vnd.github.machine-man-preview+json"
    return uri, headers, body

github.pre_request = change_app_header


@app.route('/')
def index():
    if 'github_token' in session:
        me = github.get('user/installations')
        return jsonify(me.data)
    return redirect(url_for('login'))


@app.route('/login')
def login():
    return github.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('github_token', None)
    return redirect(url_for('index'))


@app.route('/authorize')
def authorized():
    resp = github.authorized_response()
    app.logger.info(resp)
    if resp is None or resp.get('access_token') is None:
        return 'Access denied: reason=%s error=%s resp=%s' % (
            request.args['error'],
            request.args['error_description'],
            resp
        )
    session['github_token'] = (resp['access_token'], '')
    me = github.get('user/installations')
    return jsonify(me.data)


def gh_issue(url, repo, owner):
    """ finds the issue number given the url, repo and owner """
    slug = slugify(urlparse(request.url).path)
    app.logger.info("slugged issue title: %s" % slug)

    # query github search endpoint
    query = {"q": "%s in:title repo:%s/%s" % (slug, owner, repo)}
    resp = github.get('search/issues', data=query)
    app.logger.info("Found %s issues in search" % resp.data.get("total_count"))
    if resp.data.get("total_count") == 0:
        return None
    elif resp.data.get("total_count") == 1:
        return resp.data.get("items")[0].get("number")
    return 0


@app.route('/comment', methods=['GET'])
def comment():
    if 'github_token' not in session:
        return redirect(url_for('login'))
    else:
        try:
            repo = 'vogxn.github.io'
            owner = 'vogxn'
            comment_json = {'owner': owner,
                            'repo': repo,
                            'body': 'This is another comment!'}
            issue_num = gh_issue(request.url, repo, owner)
            if issue_num is None:
                issue_json = {'title': slugify(urlparse(request.url).path)}
                github.post('repos/%s/%s/issues'.format(owner, repo),
                            data=issue_json, format='json')
                app.logger.info("created a new root issue")
            schema = CommentSchema(strict=True)
            comment, errors = schema.load(comment_json)
            comment_endpoint = '/'.join(['repos', comment.owner, comment.repo,
                                         'issues', str(issue_num), 'comments'])
            github.post(comment_endpoint, data=comment_json, format='json')
            app.logger.info("Commenting at: %s" % comment_endpoint)
            resp = github.get(comment_endpoint)
            return jsonify(resp.data)
        except json.JSONDecodeError:
            return 422
        except ValidationError as err:
            return err.messages


@app.route('/register', methods=['GET'])
def register():
    app.logger.info(request.args)
    with database.transaction():
        Installation.create(ghid=request.args['installation_id'],
                            repo='', owner='')
    return


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')


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
