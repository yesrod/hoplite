import traceback
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


    # dumps everything
    # TODO: Remove me later, only here for troubleshooting purposes
    @app.route('/v1/shdata', methods=['GET'])
    def api_shdata():
        global instance
        return response(False, '200', {'shdata': instance.ShData})


    # dumps the entire config
    # TODO: Remove me later, only here for troubleshooting purposes
    @app.route('/v1/config', methods=['GET'])
    def api_config():
        global instance
        return response(False, '200', {'config': instance.ShData['config']})


    # dumps all data
    # TODO: Remove me later, only here for troubleshooting purposes
    @app.route('/v1/data', methods=['GET'])
    def api_data():
        global instance
        return response(False, '200', {'data': instance.ShData['data']})


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
    @app.route('/v1/hx/<index>/<channel>/<action>', methods=['GET'])
    @app.route('/v1/hx/<index>/<channel>', methods=['GET'])
    @app.route('/v1/hx/<index>', methods=['GET'])
    @app.route('/v1/hx', methods=['GET'])
    def api_keg(index=None, channel=None, action=None):
        global instance
        # /v1/hx/
        if index == None and channel == None and action == None:
            hxs = dict()
            try:
                instance.debug_msg("get keg config")
                hxs_config = instance.ShData['config']['hx']
                instance.debug_msg("enumerate hx")
                for index, hx in enumerate(hxs_config):
                    instance.debug_msg("hx %s" % index)
                    hxs[index] = hx

                    instance.debug_msg("enumerate channels")
                    chan = ('A', 'B')
                    for chan_index, channel in enumerate(chan):
                        try:
                            instance.debug_msg("update weight index %s chan %s" % (index, channel))
                            hxs[index]['channels'][channel]['weight'] = instance.ShData['data']['weight'][index][chan_index]
                        except ( IndexError, KeyError, ValueError ):
                            instance.debug_msg("index %s chan %s weight fail" % (index, channel))
                            try:
                                hxs[index]['channels'][channel]['weight'] = -1
                            except ( IndexError, KeyError, ValueError ):
                                instance.debug_msg("index %s chan %s doesn't exist" % (index, channel))

            except ( IndexError, KeyError, ValueError ) as e:
                traceback.print_exc()

            return response(False, 200, {'hx_list': hxs})

        # /v1/hx/<index>
        elif index != None and channel == None and action == None:
            try:
                instance.debug_msg("hx %s" % index)
                hx = instance.ShData['config']['hx'][int(index)]

                instance.debug_msg("enumerate channels")
                chan = ('A', 'B')
                for chan_index, channel in enumerate(chan):
                    instance.debug_msg("update weight index %s chan %s" % (index, channel))
                    try:
                        hx['channels'][channel]['weight'] = instance.ShData['data']['weight'][int(index)][chan_index]
                    except ( IndexError, KeyError, ValueError ):
                        instance.debug_msg("index %s chan %s weight fail" % (index, channel))
                        try:
                            hx['channels'][channel]['weight'] = -1
                        except ( IndexError, KeyError, ValueError ):
                            instance.debug_msg("index %s chan %s doesn't exist" % (index, channel))

                message = response(False, 200, {'hx': hx} )

            except ( IndexError, KeyError, ValueError ):
                message = error(400, 'No such index %s' % index )

            return message

        # /v1/hx/<index>/<channel>
        # /v1/hx/<index>/(pd_sck|dout)
        elif index != None and channel != None and action == None:
            try:
                if channel == 'A':
                    chan_index = 0
                elif channel == 'B':
                    chan_index = 1
                elif channel == 'pd_sck' or channel == 'dout':
                    chan_index = None
                else:
                    return error(400, 'No such channel %s at index %s' % ( channel, index ) )

                if chan_index != None:
                    chan_data = instance.ShData['config']['hx'][int(index)]['channels'][channel]
                    try:
                        chan_data['weight'] = instance.ShData['data']['weight'][int(index)][chan_index]
                    except ( IndexError, KeyError, ValueError ):
                        chan_data['weight'] = -1
                    message = response(False, 200, {'channel': chan_data} )
                else:
                    message = response(False, 200, {channel: instance.ShData['config']['hx'][int(index)][channel]})

            except ( IndexError, KeyError, ValueError ):
                message = error(400, 'No such channel %s at index %s' % ( channel, index ) )

            return message

        # /v1/hx/<index>/<channel>/<action>
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

                elif action == 'co2':
                    try:
                        message = response(False, '200', {'name': chan_config['co2']})
                    except KeyError:
                        message = response(False, '200', {'name': False})

                else:
                    message = error(400, '%s undefined for channel %s at index %s' % ( action, channel, index ) )

            except ( IndexError, KeyError, ValueError ):
                message = error(400, 'No such channel %s at index %s' % ( channel, index ) )

            return message

        else:
            return error(400, 'Malformed request: index=%s channel=%s action=%s' % ( index, channel, action ) )


    # custom 404, JSON format
    @app.errorhandler(404)
    def page_not_found(e):
        return error(404, str(e)), 404


    # custom 500, JSON format
    @app.errorhandler(500)
    def internal_error(e):
        return error(500, str(e)), 500
