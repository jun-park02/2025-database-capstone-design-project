from flask import Flask
from module.login import bcrypt

def create_app(config_object=None):
    app = Flask(__name__)
    if config_object:
        app.config.from_object(config_object)

    bcrypt.init_app(app)

    return app