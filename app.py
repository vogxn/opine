import json
import requests
import logging

from flask import Flask, redirect, url_for, session, request, jsonify
from flask_oauthlib.client import OAuth
from flask_cors import CORS
from werkzeug import security
from urllib.parse import urlparse
from slugify import slugify
from marshmallow import ValidationError

from models import *
from settings import *
from comment import *

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
cors = CORS(app)
oauth = OAuth(app)


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


# TODO: remove magic number. only for testing
def get_comments(owner, repo, num=7):
    """ Get comments on issue with `num` """
    resp = requests.get("/".join([API_URL, "repos", owner, repo, "issues",
                                  str(num), "comments"]))
    cs = CommentSchema(many=True)
    # serialize into comment objects for opine
    comments = cs.load(resp.json())
    # deserialize into json comment response from opine
    return jsonify(cs.dump(comments.data, many=True).data)


@app.route('/', methods=['GET'])
def index():
    if 'gh_token' in session:
        owner = session.get('gh_owner')
        repo = session.get('gh_repo')
        return get_comments(owner, repo)
    return redirect(url_for('login'))


@app.route('/login', methods=['POST'])
def login():
    return github.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('gh_token', None)
    session.pop('gh_owner', None)
    session.pop('gh_repo', None)
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


def gh_issue(url, session):
    """ finds the issue number given the url, repo and owner """
    slug = slugify(urlparse(request.url).path)
    app.logger.info("slugged issue title: %s" % slug)
    owner, repo = session.get('gh_owner'), session.get('gh_repo')

    # query github search endpoint
    query = {"q": "%s in:title repo:%s/%s" % (slug, owner, repo)}
    resp = github.get('search/issues', data=query)
    app.logger.info("Found %s issues in search" % resp.data.get("total_count"))
    if resp.data.get("total_count") == 0:
        return None
    elif resp.data.get("total_count") == 1:
        return resp.data.get("items")[0].get("number")
    return 0


def gh_create_root_comment(url, session):
    issue_json = {'title': slugify(urlparse(url).path)}
    owner, repo = session.get('gh_owner'), session.get('gh_repo')
    github.post('repos/%s/%s/issues'.format(owner, repo),
                data=issue_json, format='json')
    app.logger.info("created a new root issue")


def post_comment(issue_num, body):
    owner, repo = session.get('gh_owner'), session.get('gh_repo')
    # form comment body and post
    cs = CommentSchema()
    comment, errors = cs.load(body)
    # TODO: handle errors
    gh_comments = '/'.join(['repos', owner, repo, 'issues', str(issue_num),
                            'comments'])
    app.logger.info("Commenting at: %s" % gh_comments)
    # TODO: handle post response
    github.post(gh_comments, data=comment_json, format='json')


@app.route('/comment', methods=['POST'])
def comment():
    if 'gh_token' not in session:
        return redirect(url_for('login'))
    else:
        try:
            issue_num = gh_issue(request.url, session)
            if issue_num is None:
                create_root_comment(request.url, session)
            body = request.get_json()
            post_comment(issue_num, body)
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
