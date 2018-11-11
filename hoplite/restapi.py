from flask import Flask, jsonify

app = Flask(__name__)
app.url_map.strict_slashes = False
instance = None

def error(code, message):
    return response(True, code, None, message)

def response(error, code, data, message=None):
    if error == True:
        status = 'error'
    elif error == False:
        status = 'ok'
    else:
        raise ValueError('error must be boolean')
    return jsonify(status=status, code=code, data=data, message=message)

class RestApi():

    def __init__(self, hoplite):
        global instance
        instance = hoplite

    def worker(self):
        global app
        app.run(use_reloader=False, host='0.0.0.0')

    # dumps the entire config
    # TODO: Remove me later, only here for troubleshooting purposes
    @app.route('/v1/config', methods=['GET'])
    def api_config():
        global instance
        return response(False, '200', {'config': instance.ShData['config']})


    # get current temperature
    @app.route('/v1/temp', methods=['GET'])
    def api_temp():
        global instance
        return response(False, 200, {'temp': instance.temp})


    # handle weight display mode
    @app.route('/v1/weight_mode', methods=['GET'])
    def api_weight_mode():
        global instance
        return response(False, 200, {'weight_mode': instance.ShData['config']['weight_mode']})


    # handle keg specific data, per channel, per index, and overall
    @app.route('/v1/keg_sensors/<index>/<channel>/<action>', methods=['GET'])
    @app.route('/v1/keg_sensors/<index>/<channel>', methods=['GET'])
    @app.route('/v1/keg_sensors/<index>', methods=['GET'])
    @app.route('/v1/keg_sensors', methods=['GET'])
    def api_keg(index=None, channel=None, action=None):
        global instance
        # /v1/keg_sensors/
        if index == None and channel == None and action == None:
            kegs = dict()
            try:
                kegs_config = instance.ShData['config']['hx']
                for index, sensor_unit in enumerate(kegs_config):
                    kegs[index] = sensor_unit

                for channel in ('A', 'B'):
                    if channel == 'A':
                        chan_index = 0
                    elif channel == 'B':
                        chan_index = 1
                    try:
                        kegs[index]['channels'][channel]['weight'] = instance.ShData['data']['weight'][index][chan_index]
                    except ( IndexError, KeyError, ValueError ):
                        kegs[index]['channels'][channel]['weight'] = -1

            except ( IndexError, KeyError, ValueError ):
                pass

            return response(False, 200, {'keg_sensors': kegs})

        # /v1/keg_sensors/<index>
        elif index != None and channel == None and action == None:
            try:
                kegs = instance.ShData['config']['hx'][int(index)]

                for channel in ('A', 'B'):
                    if channel == 'A':
                        chan_index = 0
                    elif channel == 'B':
                        chan_index = 1
                    try:
                        kegs['channels'][channel]['weight'] = instance.ShData['data']['weight'][int(index)][chan_index]
                    except ( IndexError, KeyError, ValueError ):
                        kegs['channels'][channel]['weight'] = -1

                message = response(False, 200, {'keg_sensor': kegs} )

            except ( IndexError, KeyError, ValueError ):
                message = error(400, 'No such index %s' % index )

            return message

        # /v1/keg_sensors/<index>/<channel>
        elif index != None and channel != None and action == None:
            try:
                chan_data = instance.ShData['config']['hx'][int(index)]['channels'][channel]

                if channel == 'A':
                    chan_index = 0
                elif channel == 'B':
                    chan_index = 1
                else:
                    return error(400, 'No such channel %s at index %s' % ( channel, index ) )

                try:
                    chan_data['weight'] = instance.ShData['data']['weight'][int(index)][chan_index]
                except ( IndexError, KeyError, ValueError ):
                    chan_data['weight'] = -1

                message = response(False, 200, {'channel': chan_data} )

            except ( IndexError, KeyError, ValueError ):
                message = error(400, 'No such channel %s at index %s' % ( channel, index ) )

            return message

        # /v1/keg_sensors/<index>/<channel>/<action>
        elif index and channel and action:
            if channel == 'A':
                chan_index = 0
            elif channel == 'B':
                chan_index = 1
            else:
                return error(400, 'No such channel %s at index %s' % ( channel, index ) )

            try:
                chan_config = instance.ShData['config']['hx'][int(index)]['channels'][channel]

                if action == 'weight':                
                    message = response(False, '200', {'weight': instance.ShData['data']['weight'][int(index)][chan_index]})

                elif action == 'name':
                    message = response(False, '200', {'name': chan_config['name']})

                elif action == 'size':
                    message = response(False, '200', {'size': chan_config['size_name']})

                elif action == 'tare':
                    message = response(False, '200', {'tare': chan_config['size'][1]})

                elif action == 'volume':
                    message = response(False, '200', {'volume': chan_config['size'][0]})

                elif action == 'offset':
                    message = response(False, '200', {'offset': chan_config['offset']})

                elif action == 'refunit':
                    message = response(False, '200', {'refunit': chan_config['refunit']})

                else:
                    message = error(400, '%s undefined for channel %s at index %s' % ( action, channel, index ) )

            except ( IndexError, KeyError, ValueError ):
                message = error(400, 'No such channel %s at index %s' % ( channel, index ) )

            return message

        else:
            return error(400, 'Malformed request: index=%s channel=%s action=%s' % ( index, channel, action ) )


    # handle CO2 data
    @app.route('/v1/co2/<action>', methods=['GET'])
    @app.route('/v1/co2', methods=['GET'])
    def api_co2(action=None):
        # /vi/co2/<action>
        try:
            chan_config = instance.ShData['config']['co2']

            if action == 'percent':
                message = response(False, '200', {'percent': instance.ShData['data']['co2']})

            elif action == 'tare':
                message = response(False, '200', {'tare': chan_config['size'][1]})

            elif action == 'volume':
                message = response(False, '200', {'volume': chan_config['size'][0]})

            elif action == 'offset':
                message = response(False, '200', {'offset': chan_config['offset']})

            elif action == 'refunit':
                message = response(False, '200', {'refunit': chan_config['refunit']})

            # /v1/co2
            elif action == None:
                message = response(False, '200',  {'co2': chan_config} )

            else:
                message = error(400, '%s undefined for CO2 channel' % action )

        except ( IndexError, KeyError, ValueError ):
            message = error(400, 'CO2 sensor not defined in config' )

        return message


    # custom 404, JSON format
    @app.errorhandler(404)
    def page_not_found(e):
        return error(404, str(e)), 404


    # custom 500, JSON format
    @app.errorhandler(500)
    def internal_error(e):
        return error(500, str(e)), 500
