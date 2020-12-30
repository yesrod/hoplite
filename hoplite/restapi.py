import traceback
from werkzeug.exceptions import BadRequest
from flask import Flask, jsonify, request

app = Flask(__name__)
app.url_map.strict_slashes = False
instance = None

import hoplite.utils as utils


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
    utils.debug_msg(instance,"enumerate channels")
    chan = ('A', 'B')
    for chan_index, channel in enumerate(chan):
        utils.debug_msg(instance,"update weight index %s chan %s" % (index, channel))
        try:
            hx['channels'][channel]['weight'] = instance.ShData['data']['weight'][int(index)][chan_index]
        except ( IndexError, KeyError, ValueError ):
            utils.debug_msg(instance,traceback.format_exc())
            utils.debug_msg(instance,"index %s chan %s weight fail" % (index, channel))
            try:
                hx['channels'][channel]['weight'] = -1
            except ( IndexError, KeyError, ValueError ):
                utils.debug_msg(instance,traceback.format_exc())
                utils.debug_msg(instance,"index %s chan %s doesn't exist" % (index, channel))
    return hx


# get all HXs, in list, with weight
def get_all_hx_with_weight():
    hxs = list()
    try:
        utils.debug_msg(instance,"get keg config")
        hxs_config = instance.ShData['config']['hx']
        utils.debug_msg(instance,"enumerate hx")
        for index, hx in enumerate(hxs_config):
            utils.debug_msg(instance,"hx %s" % index)
            hxs.insert(index, add_weight_to_hx(index, hx))
    except ( IndexError, KeyError, ValueError ):
        utils.debug_msg(instance,traceback.format_exc())
    return hxs


# validate data from PUT and POST
def validate_request():
    try:
        data = request.json
        utils.debug_msg(instance,data)
    except BadRequest:
        utils.debug_msg(instance,traceback.format_exc())
        utils.debug_msg(instance,"request is not valid JSON: %s" % request.get_data())
        data = None
    return data


# add a channel
def add_channel(index, channel, data):
    if channel != 'A' and channel != 'B':
        return error(400, 'No such channel %s at index %s' % ( channel, index ) )

    required_keys = ('name', 'size', 'tare', 'volume')
    optional_keys = {'co2': False, 'refunit': 0, 'offset': 0}
    submission = dict()
    for key in required_keys:
        if not key in data.keys():
            return error(400, 'Key %s is required' % key)
        submission[key] = data[key]
    for key in optional_keys.keys():
        if not key in data.keys():
            submission[key] = optional_keys[key]
        else:
            submission[key] = data[key]
    try:
        instance.ShData['config']['hx'][int(index)]['channels'][channel] = submission
        instance.shmem_write()
        return response(False, 200, {channel: submission}, '%s successfully created or updated' % channel)
    except IndexError:
        utils.debug_msg(instance,traceback.format_exc())
        return error(400, 'No existing index %s' % index)


# add an index
def add_index(data):
    new_index = dict()
    for key in ('pd_sck', 'dout'):
        if not key in data.keys():
            return error(400, 'Key %s is required' % key)
        new_index[key] = data[key]

    new_index['channels'] = dict()
    if not 'channels' in data.keys():
        return error(400, 'channels must be a JSON object containing one or more channels')
    try:
        for channel in data['channels'].keys():
            if channel not in ('A', 'B'):
                return error(400, 'Invalid channel %s - must be A or B' % channel )

            required_keys = ('name', 'size', 'tare', 'volume')
            optional_keys = {'co2': False, 'refunit': 0, 'offset': 0}
            submission = dict()
            for key in required_keys:
                if not key in data['channels'][channel].keys():
                    return error(400, 'Channel %s key %s is required' % (channel, key))
                submission[key] = data['channels'][channel][key]
            for key in optional_keys.keys():
                if not key in data['channels'][channel].keys():
                    submission[key] = optional_keys[key]
                else:
                    submission[key] = data['channels'][channel][key]
            new_index['channels'][channel] = submission

    except AttributeError:
        utils.debug_msg(instance,traceback.format_exc())
        return error(400, 'channels must be a JSON object containing one or more channels also represented as JSON objects')

    instance.ShData['config']['hx'].append(new_index)
    instance.shmem_write()
    last_index = len(instance.ShData['config']['hx']) - 1
    return response(False, 200, {last_index: new_index}, 'Index %s successfully created or updated' % last_index)


# delete a channel
def delete_channel(index, channel):
    try:
        deleted_data = instance.ShData['config']['hx'][int(index)]['channels'][channel]
        del instance.ShData['config']['hx'][int(index)]['channels'][channel]
        instance.shmem_write()
        return response(False, 200, {channel: deleted_data}, '%s successfully deleted' % channel)
    except KeyError:
        utils.debug_msg(instance,traceback.format_exc())
        return error(400, 'No existing channel %s' % channel)
    except IndexError:
        utils.debug_msg(instance,traceback.format_exc())
        return error(400, 'No existing index %s' % index)


# delete an index
def delete_index(index):
    try:
        deleted_data = instance.ShData['config']['hx'][int(index)]
        del instance.ShData['config']['hx'][int(index)]
        instance.shmem_write()
        return response(False, 200, {index: deleted_data}, '%s successfully deleted' % index)
    except IndexError:
        utils.debug_msg(instance,traceback.format_exc())
        return error(400, 'No existing index %s' % index)


class RestApi():

    def __init__(self, hoplite):
        global instance
        instance = hoplite


    def worker(self, host=None, port=None):
        global app
        app.run(use_reloader=False, host=host, port=port)


    # dumps everything
    # TODO: Remove me later, only here for troubleshooting purposes
    @staticmethod
    @app.route('/v1/shdata', methods=['GET'])
    def get_shdata():
        global instance
        return response(False, '200', {'shdata': instance.ShData})


    # dumps the entire config
    # TODO: Remove me later, only here for troubleshooting 
    @staticmethod
    @app.route('/v1/config', methods=['GET'])
    def get_config():
        global instance
        return response(False, '200', {'config': instance.ShData['config']})


    # dumps all data
    # TODO: Remove me later, only here for troubleshooting purposes
    @staticmethod
    @app.route('/v1/data', methods=['GET'])
    def get_data():
        global instance
        return response(False, '200', {'data': instance.ShData['data']})


    # get current temperature
    @staticmethod
    @app.route('/v1/temp', methods=['GET'])
    def get_temp():
        global instance
        return response(False, 200, {'temp': instance.temp})


    # get weight display mode
    @staticmethod
    @app.route('/v1/weight_mode', methods=['GET'])
    def get_weight_mode():
        global instance
        return response(False, 200, {'weight_mode': instance.ShData['config']['weight_mode']})


    # set weight display mode
    @staticmethod
    @app.route('/v1/weight_mode', methods=['PUT'])
    def set_weight_mode():
        data = validate_request()
        if data == None:
            return error(400, 'Bad Request - invalid JSON')
        else:
            try:
                weight_mode = data['weight_mode']
            except KeyError:
                utils.debug_msg(instance,traceback.format_exc())
                return error(400, 'Bad Request - no weight_mode in request')
            valid_modes = ('as_kg_gross', 'as_kg_net', 'as_pint', 'as_pct')
            if not weight_mode in valid_modes:
                return error(400, 'Bad Request - invalid weight_mode %s' % weight_mode)
            else:
                instance.ShData['config']['weight_mode'] = weight_mode
                instance.shmem_write()
                return response(False, 200, {'weight_mode': weight_mode}, 'weight_mode successfully updated' )


    # get display model
    @staticmethod
    @app.route('/v1/display', methods=['GET'])
    def get_display():
        global instance
        return response(False, 200, {'display': instance.ShData['config']['display']})


    # set display model
    @staticmethod
    @app.route('/v1/display', methods=['PUT'])
    def set_display():
        data = validate_request()
        if data == None:
            return error(400, 'Bad Request - invalid JSON')
        else:
            try:
                display = data['display']
            except KeyError:
                utils.debug_msg(instance,traceback.format_exc())
                return error(400, 'Bad Request - no display in request')
            instance.ShData['config']['display'] = display
            instance.shmem_write()
            return response(False, 200, {'display': display}, 'display successfully updated' )


    # root element for api v1
    # not much here past /v1/hx really
    @staticmethod
    @app.route('/v1', methods=['GET'])
    def get_root():
        global instance
        root = dict()
        root['hx_list'] = get_all_hx_with_weight()
        root['display'] = instance.ShData['config']['display']
        root['weight_mode'] = instance.ShData['config']['weight_mode']
        root['temp'] = instance.temp
        return response(False, 200, {'v1': root})


    # handle keg specific data, per channel, per index, and overall
    @staticmethod
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
                utils.debug_msg(instance,"hx %s" % index)
                hx = instance.ShData['config']['hx'][int(index)]
                hx = add_weight_to_hx(index, hx)

                message = response(False, 200, {'hx': hx} )

            except ( IndexError, KeyError, ValueError ):
                utils.debug_msg(instance,traceback.format_exc())
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
                        utils.debug_msg(instance,traceback.format_exc())
                        chan_data['weight'] = -1
                    message = response(False, 200, {'channel': chan_data} )
                else:
                    message = response(False, 200, {channel: instance.ShData['config']['hx'][int(index)][channel]})

            except ( IndexError, KeyError, ValueError ):
                utils.debug_msg(instance,traceback.format_exc())
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
                valid_actions = ['name', 'size', 'offset', 'refunit', 'tare', 'volume']

                if action == 'weight':
                    message = response(False, '200', {'weight': instance.ShData['data']['weight'][int(index)][chan_index]})

                elif action in valid_actions:
                    message = response(False, '200', {action: chan_config[action]})

                elif action == 'co2':
                    try:
                        message = response(False, '200', {'name': chan_config['co2']})
                    except KeyError:
                        utils.debug_msg(instance,traceback.format_exc())
                        message = response(False, '200', {'name': False})

                else:
                    message = error(400, '%s undefined for channel %s at index %s' % ( action, channel, index ) )

            except ( IndexError, KeyError, ValueError ):
                utils.debug_msg(instance,traceback.format_exc())
                message = error(400, 'No such channel %s at index %s' % ( channel, index ) )

            return message

        else:
            return error(400, 'Malformed request: index=%s channel=%s action=%s' % ( index, channel, action ) )


    @staticmethod
    @app.route('/v1/hx/<index>/<channel>/<action>', methods=['PUT'])
    @app.route('/v1/hx/<index>/<channel>', methods=['PUT', 'POST', 'DELETE'])
    @app.route('/v1/hx/<index>', methods=['DELETE'])
    @app.route('/v1/hx/', methods=['POST'])
    def set_keg(index=None, channel=None, action=None):
        data = validate_request()
        utils.debug_msg(instance,data)
        if data == None and request.method != 'DELETE':
            return error(400, 'Bad Request - invalid JSON')
        # /v1/hx/
        elif index == None and channel == None and action == None:
            return add_index(data)
        # /v1/hx/<index>
        elif index != None and channel == None and action == None:
            return delete_index(index)
        # /v1/hx/<index>/<channel>
        # /v1/hx/<index>/(pd_sck|dout)
        elif index != None and channel != None and action == None:
            if channel == 'A':
                chan_index = 0
            elif channel == 'B':
                chan_index = 1
            elif channel == 'pd_sck' or channel == 'dout':
                chan_index = None
            else:
                return error(400, 'No such channel %s at index %s' % ( channel, index ) )

            if chan_index == None and request.method == 'PUT':
                try:
                    instance.ShData['config']['hx'][int(index)]['channels'][channel] = data[channel]
                except ( IndexError, KeyError, ValueError ):
                    utils.debug_msg(instance,traceback.format_exc())
                    return error(400, 'No %s at index %s' % ( channel, index ) )
                return response(False, 200, {channel: data[channel]}, '%s successfully updated' % action)
            elif request.method == 'POST' and chan_index != None:
                return add_channel(index, channel, data)

            elif request.method == 'DELETE' and chan_index != None:
                try:
                    deleted_data = instance.ShData['config']['hx'][int(index)]['channels'][channel]
                    del instance.ShData['config']['hx'][int(index)]['channels'][channel]
                    instance.shmem_write()
                    return response(False, 200, {channel: deleted_data}, '%s successfully deleted' % channel)
                except KeyError:
                    utils.debug_msg(instance,traceback.format_exc())
                    return error(400, 'No existing channel %s' % channel)

            else:
                return error(400, '%s not supported for %s' % (request.method, channel))

        # /v1/hx/<index>/<channel>/<action>
        elif index and channel and action:
            if channel == 'A':
                chan_index = 0
            elif channel == 'B':
                chan_index = 1
            else:
                return error(400, 'No such channel %s at index %s' % ( channel, index ) )

            if request.method != 'PUT':
                return error(400, '%s not supported for %s' % (request.method, action))

            try:
                valid_actions = ['name', 'size', 'offset', 'refunit', 'tare', 'volume', 'co2']

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
                        utils.debug_msg(instance,traceback.format_exc())
                        message = error(400, 'Bad Request - no %s in request' % action)

                else:
                    message = error(400, '%s undefined for channel %s at index %s' % ( action, channel, index ) )

            except ( IndexError, KeyError, ValueError ):
                utils.debug_msg(instance,traceback.format_exc())
                message = error(400, 'No such channel %s at index %s' % ( channel, index ) )

            return message

        else:
            return error(400, 'Malformed request: index=%s channel=%s action=%s' % ( index, channel, action ) )


    # custom 400, JSON format
    @staticmethod
    @app.errorhandler(400)
    def bad_request(e):
        return error(400, str(e))


    # custom 404, JSON format
    @staticmethod
    @app.errorhandler(404)
    def page_not_found(e):
        return error(404, str(e))


    # custom 405, JSON format
    @staticmethod
    @app.errorhandler(405)
    def method_not_allowed(e):
        return error(405, str(e))


    # custom 500, JSON format
    @staticmethod
    @app.errorhandler(500)
    def internal_error(e):
        return error(500, str(e))
