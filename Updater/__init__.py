import os
from flask import Flask, redirect
from . import main
from flask import send_from_directory





def create_app():
    # create the app
    app = Flask(__name__)

    app.register_blueprint(main.bp)
    @app.route('/')
    def login():
        return redirect('/auth')
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
                            

    return app
