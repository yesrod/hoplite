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


    # handle weight display mode
    @app.route('/api/weight_mode')
    def api_weight_mode():
        global instance
        return jsonify(weight_mode=instance.ShData['config']['weight_mode'])


    # handle keg specific data per channel
    # /api/keg/<index>/<channel>/<weight>
    @app.route('/api/keg/<index>/<channel>/<action>')
    def api_keg(index, channel, action):
        if channel == 'A':
            chan_index = 0
        elif channel == 'B':
            chan_index = 1
        else:
            return error(400, 'Channel %s out of range at index %s' % ( channel, index ) )

        try:
            chan_config = instance.ShData['config']['hx'][int(index)]['channels'][channel]

            if action == 'weight':                
                message = jsonify(weight=instance.ShData['data']['weight'][int(index)][chan_index])

            elif action == 'name':
                message = jsonify(name=chan_config['name'])

            elif action == 'size':
                message = jsonify(size=chan_config['size_name'])

            elif action == 'tare':
                message = jsonify(tare=chan_config['size'][1])

            elif action == 'volume':
                message = jsonify(volume=chan_config['size'][0])

            elif action == 'offset':
                message = jsonify(offset=chan_config['offset'])

            elif action == 'refunit':
                message = jsonify(refunit=chan_config['refunit'])

            else:
                message = error(400, '%s undefined for channel %s at index %s' % ( action, channel, index ) )

        except ( IndexError, KeyError, ValueError ):
            message = error(400, 'Channel %s at index %s not defined in config' % ( channel, index ) )

        return message


    # handle CO2 data
    @app.route('/api/co2/<action>')
    def api_co2(action):
        try:
            chan_config = instance.ShData['config']['co2']

            if action == 'percent':
                message = jsonify(percent=instance.ShData['data']['co2'])

            elif action == 'tare':
                message = jsonify(tare=chan_config['size'][1])

            elif action == 'volume':
                message = jsonify(volume=chan_config['size'][0])

            elif action == 'offset':
                message = jsonify(offset=chan_config['offset'])

            elif action == 'refunit':
                message = jsonify(refunit=chan_config['refunit'])

            else:
                message = error(400, '%s undefined for CO2 channel' % action )

        except ( IndexError, KeyError, ValueError ):
            message = error(400, 'CO2 sensor not defined in config' )

        return message


    # custom 404, JSON format
    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify(error=404, text=str(e)), 404


    # custom 500, JSON format
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(error=500, text=str(e)), 500
