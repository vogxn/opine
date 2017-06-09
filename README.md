Many blogs are written using github pages - so every blog has an associated git
repository. This project is a [Github App](https://developer.github.com/apps/)
that provides a [shim](https://en.wikipedia.org/wiki/Shim_(computing)) to post
comments from such blogs as comments to issues in the associated git
repository.

Userflows
=========

Admin
-----
- github user installs opine app from the github marketplace
- after installation opine.io prompts user to register with - blog url, git repo, github handle
- this completes the installation

Commenter
---------
- commenter signs in via github
- commenter leaves comment
- opine.io takes comment, associates it as an issue comment on admin's github pages repo
- opine.io posts comment text as issue comment body


REST API
========

When a user goes to a blog and wants to leave a comment, `/login` will redirect
him to authenticate using his github credentials. 

--

```
HTTP/1.1 POST /login
Content-Type: application/json; charset=utf-8
Date: Mon, 05 Jun 2017 11:52:49 GMT

{"ghid": <app-installation-id>}
```

This creates an access token behind the scenes for the session.

In order to comment you have to pass

```
HTTP/1.1 POST /comment
Content-Type: application/json; charset=utf-8
Date: Mon, 05 Jun 2017 11:55:39 GMT

{"body": "my comment here"}
```

Development
===========

You can run the app locally by setting up the python environment first and then
starting a gunicorn server

```
(virtualenv) ~$ python setup.py install
(virtualenv) ~$ gunicorn opine:app --log-file -

```

Enhancements
============

- reCAPTCHA support
- embedding in static site generators - hugo, jekyll etc
