import requests
from slugify import slugify
from comment import CommentSchema
from settings import API_URL


class GithubCommentProxy(object):
    """ GithubCommentProxy is the shim between Opine's API and Github API for
    comments. Currently update and delete operations are unsupported """

    def __init__(self):
        self._valid = False
        self.owner, self.repo, self.connection = None, None, None

    def connect(self, owner, repo, connection):
        self.owner = owner
        self.repo = repo
        self.connection = connection
        self._valid = True

    @property
    def valid(self):
        return self._valid

    def get(self, title):
        """ Get comments on issue with given title """
        num = self.search_head(title)
        resp = requests.get("/".join([API_URL, "repos", self.owner, self.repo,
                                      "issues", str(num), "comments"]))
        cs = CommentSchema(many=True)
        # serialize into comment objects for opine
        comments = cs.load(resp.json())
        # deserialize into json comment response from opine
        s_comments = cs.dump(comments.data, many=True).data
        return s_comments

    def search_head(self, title):
        """ finds the associated issue number given the title """
        slug = slugify(title)
        # query github search endpoint
        query = {"q": "%s in:title repo:%s/%s" % (slug, self.owner, self.repo)}
        resp = self.connection.get('search/issues', data=query)
        assert resp.status == 200
        if resp.data.get("total_count") == 0:
            return None
        elif resp.data.get("total_count") == 1:
            return resp.data.get("items")[0].get("number")
        else:
            return 0

    def create_head(self, title):
        issue_json = {'title': slugify(title)}
        res = self.connection.post('repos/%s/%s/issues'.format(self.owner,
                                                               self.repo),
                                   data=issue_json, format='json')
        return res.status == 200

    def create(self, payload):
        cs = CommentSchema()
        comment, errors = cs.load(payload)  # TODO: handle errors
        issue_num = self.search_head(comment.title)
        if issue_num is None:
            self.create_head_comment(comment.title)
        gh_comments = '/'.join(['repos', self.owner, self.repo, 'issues',
                                str(issue_num), 'comments'])
        res = self.connection.post(gh_comments, data=payload, format='json')
        return res.status == 200

    def update(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError
