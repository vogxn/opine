Many blogs are written using github pages - so every blog has an associated git
repository. This project is a [Github App](https://developer.github.com/apps/)
that provides a [shim](https://en.wikipedia.org/wiki/Shim_(computing)) to post
comments from such blogs as comments to issues in the associated git
repository.


Design
======

When a user goes to a blog and wants to leave a comment, `/login` will redirect
him to authenticate using his github credentials. 

--

```
HTTP/1.1 POST /login
Content-Type: application/json; charset=utf-8
Date: Mon, 05 Jun 2017 11:52:49 GMT

{"owner": <github-handle-of-owner-of-blog>, "repo": <github-repo-for-blog>", "title": "Page Title Of Blog Post"}
```

This creates an access token behind the scenes for the session.

In order to comment you have to pass

```
HTTP/1.1 POST /comment
Content-Type: application/json; charset=utf-8
Date: Mon, 05 Jun 2017 11:55:39 GMT

{"title": "Page Title Of Blog Post", "body": "my comment here"}
```


Flow 1:
======
- User is unauthorized
  - save session data
- Redirect to /login
  - shortcode lookup => (installation_id, repo, owner)
  - save to session data
- Get OAuth Access Token
- Redirect to /comment with comment data in body
  - prepare github comment/issue
  - POST comment/issue
  - update counters in stats
  - return full issue with comments JSON in response


Database
========

users:
| pk | installation_id | shortcode | repo | owner | active | created | updated |

stats:
| pk | installation_id | comments | updated |


sessions:
| pk | sid | active | expiry |
