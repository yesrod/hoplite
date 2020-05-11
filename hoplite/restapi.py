import traceback
from werkzeug.exceptions import BadRequest
from flask import Flask, jsonify, request

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
    return jsonify(status=status, code=code, data=data, message=message), code


# enumerate HX711 channels
def add_weight_to_hx(index, hx):
    instance.debug_msg("enumerate channels")
    chan = ('A', 'B')
    for chan_index, channel in enumerate(chan):
        instance.debug_msg("update weight index %s chan %s" % (index, channel))
        try:
            hx['channels'][channel]['weight'] = instance.ShData['data']['weight'][int(index)][chan_index]
        except ( IndexError, KeyError, ValueError ):
            traceback.print_exc()
            instance.debug_msg("index %s chan %s weight fail" % (index, channel))
            try:
                hx['channels'][channel]['weight'] = -1
            except ( IndexError, KeyError, ValueError ):
                traceback.print_exc()
                instance.debug_msg("index %s chan %s doesn't exist" % (index, channel))
    return hx


# get all HXs, in list, with weight
def get_all_hx_with_weight():
    hxs = list()
    try:
        instance.debug_msg("get keg config")
        hxs_config = instance.ShData['config']['hx']
        instance.debug_msg("enumerate hx")
        for index, hx in enumerate(hxs_config):
            instance.debug_msg("hx %s" % index)
            hxs.insert(index, add_weight_to_hx(index, hx))
    except ( IndexError, KeyError, ValueError ):
        traceback.print_exc()
    return hxs


# validate data from PUT and POST
def validate_request():
    try:
        data = request.json
        instance.debug_msg(data)
    except BadRequest:
        traceback.print_exc()
        instance.debug_msg("request is not valid JSON: %s" % request.get_data())
        data = None
    return data


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
    def get_shdata():
        global instance
        return response(False, '200', {'shdata': instance.ShData})


    # dumps the entire config
    # TODO: Remove me later, only here for troubleshooting purposes
    @app.route('/v1/config', methods=['GET'])
    def get_config():
        global instance
        return response(False, '200', {'config': instance.ShData['config']})


    # dumps all data
    # TODO: Remove me later, only here for troubleshooting purposes
    @app.route('/v1/data', methods=['GET'])
    def get_data():
        global instance
        return response(False, '200', {'data': instance.ShData['data']})


    # get current temperature
    @app.route('/v1/temp', methods=['GET'])
    def get_temp():
        global instance
        return response(False, 200, {'temp': instance.temp})


    # handle weight display mode
    @app.route('/v1/weight_mode', methods=['GET'])
    def get_weight_mode():
        global instance
        return response(False, 200, {'weight_mode': instance.ShData['config']['weight_mode']})


    # set weight display mode
    @app.route('/v1/weight_mode', methods=['PUT'])
    def set_weight_mode():
        data = validate_request()
        if data == None:
            return error(400, 'Bad Request - invalid JSON')
        else:
            try:
                weight_mode = data['weight_mode']
            except KeyError:
                traceback.print_exc()
                return error(400, 'Bad Request - no weight_mode in request')
            valid_modes = ('as_kg_gross', 'as_kg_net', 'as_pint', 'as_pct')
            if not weight_mode in valid_modes:
                return error(400, 'Bad Request - invalid weight_mode %s' % weight_mode)
            else:
                instance.ShData['config']['weight_mode'] = weight_mode
                instance.shmem_write()
                return response(False, 200, {'weight_mode': weight_mode}, 'weight_mode successfully updated' )


    # root element for api v1
    # not much here past /v1/hx really
    @app.route('/v1', methods=['GET'])
    def get_root():
        global instance
        root = dict()
        root['hx_list'] = get_all_hx_with_weight()
        return response(False, 200, {'v1': root})


    # handle keg specific data, per channel, per index, and overall
    @app.route('/v1/hx/<index>/<channel>/<action>', methods=['GET'])
    @app.route('/v1/hx/<index>/<channel>', methods=['GET'])
    @app.route('/v1/hx/<index>', methods=['GET'])
    @app.route('/v1/hx', methods=['GET'])
    def get_keg(index=None, channel=None, action=None):
        global instance
        # /v1/hx/
        if index == None and channel == None and action == None:
            hxs = get_all_hx_with_weight()
            return response(False, 200, {'hx_list': hxs})

        # /v1/hx/<index>
        elif index != None and channel == None and action == None:
            try:
                instance.debug_msg("hx %s" % index)
                hx = instance.ShData['config']['hx'][int(index)]
                hx = add_weight_to_hx(index, hx)

                message = response(False, 200, {'hx': hx} )

            except ( IndexError, KeyError, ValueError ):
                traceback.print_exc()
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
                        traceback.print_exc()
                        chan_data['weight'] = -1
                    message = response(False, 200, {'channel': chan_data} )
                else:
                    message = response(False, 200, {channel: instance.ShData['config']['hx'][int(index)][channel]})

            except ( IndexError, KeyError, ValueError ):
                traceback.print_exc()
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
                        traceback.print_exc()
                        message = response(False, '200', {'name': False})

                else:
                    message = error(400, '%s undefined for channel %s at index %s' % ( action, channel, index ) )

            except ( IndexError, KeyError, ValueError ):
                traceback.print_exc()
                message = error(400, 'No such channel %s at index %s' % ( channel, index ) )

            return message

        else:
            return error(400, 'Malformed request: index=%s channel=%s action=%s' % ( index, channel, action ) )


    @app.route('/v1/hx/<index>/<channel>/<action>', methods=['PUT'])
    @app.route('/v1/hx/<index>/<channel>', methods=['POST', 'DELETE'])
    @app.route('/v1/hx/<index>', methods=['POST', 'DELETE'])
    def set_keg(index=None, channel=None, action=None):
        data = validate_request()
        instance.debug_msg(data)
        if data == None:
            return error(400, 'Bad Request - invalid JSON')
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
                valid_actions = ['name', 'size_name', 'offset', 'refunit', 'co2']

                if action == 'weight':
                    message = error('400', 'Bad Request - cannot manually specify weight')

                elif action in valid_actions:
                    try:
                        if action == 'co2':
                            if data[action] != True and data[action] != False:
                                return error(400, 'Bad Request - %s must be true or false' % action)
                        instance.ShData['config']['hx'][int(index)]['channels'][channel][action] = data[action]
                        instance.shmem_write()
                        message = response(False, 200, {action: data[action]}, '%s successfully updated' % action)
                    except KeyError:
                        traceback.print_exc()
                        message = error(400, 'Bad Request - no %s in request' % action)

                elif action == 'tare' or action == 'volume':
                    if action == 'tare':
                        var_offset = 1
                    else:
                        var_offset = 0
                    try:
                        instance.ShData['config']['hx'][int(index)]['channels'][channel]['size'][var_offset] = float(data[action])
                        instance.shmem_write()
                        message = response(False, 200, {action: data[action]}, '%s successfully updated' % action)
                    except KeyError:
                        traceback.print_exc()
                        message = error(400, 'Bad Request - no %s in request' % action)

                else:
                    message = error(400, '%s undefined for channel %s at index %s' % ( action, channel, index ) )

            except ( IndexError, KeyError, ValueError ):
                traceback.print_exc()
                message = error(400, 'No such channel %s at index %s' % ( channel, index ) )

            return message

        else:
            return error(400, 'Malformed request: index=%s channel=%s action=%s' % ( index, channel, action ) )


    # custom 400, JSON format
    @app.errorhandler(400)
    def bad_request(e):
        return error(400, str(e))


    # custom 404, JSON format
    @app.errorhandler(404)
    def page_not_found(e):
        return error(404, str(e))


    # custom 405, JSON format
    @app.errorhandler(405)
    def method_not_allowed(e):
        return error(405, str(e))


    # custom 500, JSON format
    @app.errorhandler(500)
    def internal_error(e):
        return error(500, str(e))
