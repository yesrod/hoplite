from flask import Flask, jsonify

app = Flask(__name__)
instance = None

def error(code, message):
    return jsonify(error=code, text=message)

class RestApi():

    def __init__(self, hoplite):
        global instance
        instance = hoplite

    def worker(self):
        global app
        app.run(use_reloader=False)

    # dumps the entire config
    # TODO: Remove me later, only here for troubleshooting purposes
    @app.route('/config')
    def api_config():
        global instance
        return jsonify(instance.ShData['config'])


    # get current temperature
    @app.route('/api/temp')
    def api_temp():
        global instance
        return jsonify(temp=instance.temp)


    # get keg specific data per channel
    # /api/keg/<index>/<channel>/<weight>
    @app.route('/api/keg/<index>/<channel>/<action>')
    def api_keg(index, channel, action):
        if channel == 'A':
            chan_index = 0
        elif channel == 'B':
            chan_index = 1
        else:
            return error(400, 'Channel %s out of range at index %s' % ( channel, index ) )

        if action == 'weight':
            try:
                chan_config = instance.ShData['config']['hx'][int(index)]['channels'][channel]
                message = jsonify(weight=instance.ShData['data']['weight'][int(index)][chan_index])
            except ( IndexError, KeyError, ValueError ):
                message = error(400, 'Channel %s at index %s not defined in config' % ( channel, index ) )
        else:
            message = error(400, '%s undefined for channel %s at index %s' % ( action, channel, index ) )
        return message


    # custom 404, JSON format
    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify(error=404, text=str(e)), 404
