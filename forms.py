from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField
from wtforms.validators import DataRequired


class RegisterForm(FlaskForm):
    ghid = HiddenField(u'App Installation ID')
    login = StringField(u'Github Username', validators=[DataRequired()])
    repo = StringField(u'Github Pages Repository', validators=[DataRequired()])
    origin = StringField(u'Blog URL')
