from flask import Flask, redirect, url_for, session, request, jsonify
from flask_oauthlib.client import OAuth
import logging


app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

github = oauth.remote_app(
    'github',
    consumer_key='Iv1.7ed784ff75a2d6cf',
    consumer_secret='90dcc676c697eae43536cdd3b8a653b6923f1c42',
    request_token_params={},
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


@app.route('/comment', methods=['GET'])
def comment():
    issue_data = {
            "title": "a new approach to not giving a shit",
            "body": "how not to give a shit about the chaos around you?"
            }
    resp = github.post('repos/vogxn/vogxn.github.io/issues', data=issue_data,
                       format='json')
    app.logger.info(resp)
    return "Issue posted successfully"


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')


if __name__ == '__main__':
    logger = logging.getLogger("github.logger")
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run(port=8080)
