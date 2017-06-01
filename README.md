Design
======

Javascript XHR
```
   https://opine.io/comment {body: 'comment text', installation_id: 1234, shortcode: 'vogxn'}
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
