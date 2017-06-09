import json
import requests
from slugify import slugify
from werkzeug import security
from flask_oauthlib.client import OAuthException
from comment import CommentSchema
from settings import API_URL, CLIENT_ID, CLIENT_SECRET

SEARCH_URL = "/".join([API_URL, 'search/issues'])


def change_app_header(uri, headers, body):
    """ Add Accept header for preview features of Github apps API """
    headers["Accept"] = "application/vnd.github.machine-man-preview+json"
    return uri, headers, body


class GithubCommentProxy(object):
    """ GithubCommentProxy is the shim between Opine's API and Github API for
    comments. Currently update and delete operations are unsupported """

    def __init__(self, oauth):
        self.client = oauth.remote_app(
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
        self.client.pre_request = change_app_header

    def configure(self, owner, repo):
        self.owner, self.repo = owner, repo

    @property
    def valid(self):
        try:
            self.client.get_request_token()
        except OAuthException:
            return False
        return True

    def get_comment_resource(self, issue_num):
        path = '/'.join(['repos', self.owner, self.repo, 'issues',
                         str(issue_num), 'comments'])
        if self.valid:
            return path
        else:
            return '/'.join([API_URL, path])

    def get(self, title):
        """ Get comments on issue with given title """
        num = self.search_head(title)
        if not num:
            return {}
        comment_resource = self.get_comment_resource(num)
        if self.valid:
            resp = self.client.get(comment_resource)
            assert resp.status == 200
            data = resp.data
        else:
            resp = requests.get(comment_resource)
            assert resp.status_code == 200
            data = resp.json()
        cs = CommentSchema(many=True)
        # serialize into comment objects for opine
        comments = cs.load(data)
        # deserialize into json comment response from opine
        s_comments = cs.dump(comments.data, many=True).data
        return s_comments

    def search_head(self, title):
        """ finds the associated issue number given the title """
        slug = slugify(title)
        # query github search endpoint
        query = {"q": "%s in:title repo:%s/%s" % (slug, self.owner, self.repo)}
        if self.valid:
            resp = self.client.get('search/issues', data=query)
            assert resp.status == 200
            data = resp.data
        else:
            resp = requests.get(SEARCH_URL, params=json.dumps(query))
            assert resp.status_code == 200
            data = resp.json()
        if data.get("total_count") == 0:
            return None
        elif data.get("total_count") == 1:
            return data.get("items")[0].get("number")
        else:
            return 0

    def create_head(self, title):
        issue_json = {'title': slugify(title)}
        res = self.client.post(
            "repos/{}/{}/issues".format(self.owner, self.repo),
            data=issue_json,
            format='json'
        )
        assert res.status == 200
        return res.get("number")

    def create(self, payload):
        """ Posts a comment to the issue associated with the post """
        cs = CommentSchema()
        comment, errors = cs.load(payload)  # TODO: handle errors
        issue_num = self.search_head(comment.title)
        if issue_num is None:
            issue_num = self.create_head(comment.title)
        res = self.client.post(
            self.get_comment_resource(issue_num),
            data=payload,
            format='json'
        )
        return res.status == 200

    def update(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError
