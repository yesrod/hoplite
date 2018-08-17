import json
from flask import Flask

app = Flask(__name__)
instance = None

class RestApi():

    def __init__(self, hoplite):
        global instance
        instance = hoplite

    def worker(self):
        global app
        app.run(use_reloader=False)

    @app.route('/config')
    def get_config():
        global instance
        return json.dumps(instance.config, indent=2)

