import os
from flask import Flask

from .admin import bp as admin_bp
from .public import bp as public_bp


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
    )

    app.secret_key = os.environ.get("SECRET_KEY", "chave-secreta-trocar")
    app.config['ADMIN_USER'] = os.environ.get("ADMIN_USER", "admin")
    app.config['ADMIN_PASS'] = os.environ.get("ADMIN_PASS", "fcee2025")

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    return app


app = create_app()
