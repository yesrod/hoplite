from flask import Flask

app = Flask(__name__)

class RestApi():

    def __init__(self, instance):
        self.instance = instance

    def worker(self):
        global app
        app.run(use_reloader=False)

    @app.route('/config')
    def get_config():
        return self.instance.config

