import sys

# Shared data

# keg data dictionary
# value is list( volume in liters, empty weight in kg )
keg_data = {
    'half_bbl': (58.6, 13.6),
    'tall_qtr_bbl': (29.3, 10),
    'short_qtr_bbl': (29.3, 10),
    'sixth_bbl': (19.5, 7.5),
    'corny': (18.9, 4),
}

# Breakout board port data
# Value is list( pd_sck, dout )
breakout_ports = {
    '1': (6, 5),
    '2': (13, 12),
    '3': (27, 17),
    '4': (25, 22),
}

# Helper functions
def debug_msg(c, message):
    if c.debug:
        print("%s::%s: %s" % (c.__class__.__name__, sys._getframe(1).f_code.co_name, message))


def as_degC(temp):
    return u'%s\u00b0C' % '{0:.1f}'.format(float(temp) / 1000.0)


def as_degF(temp):
    real_c = float(temp) / 1000.0
    deg_f = real_c * (9.0/5.0) + 32.0
    return u'%s\u00b0F' % '{0:.1f}'.format(deg_f)

def as_kg(val):
    return "%s kg" % "{0:.2f}".format(val / 1000.0)


def as_pint(val):
    return '%s pt.' % int(val / 473)


def format_weight(val, mode, tare=None, cap=None):
    if mode == None:
        mode = 'as_kg_gross'

    if mode == 'as_kg_gross':
        return as_kg(val)

    elif mode == 'as_kg_net':
        if tare == None:
            raise ValueError('tare must not be None when using as_kg_net')
        else:
            return as_kg(val - tare)

    elif mode == 'as_pint':
        if tare == None:
            raise ValueError('tare must not be None when using as_pint')
        else:
            return as_pint(val - tare)

    elif mode == 'as_pct':
        if tare == None:
            raise ValueError('tare must not be None when using as_pct')
        elif max == None:
            raise ValueError('max must not be None when using as_pct')
        else:
            return "%s%%" % int(((val - tare) / cap) * 100)

    else:
        raise ValueError('bad mode %s' % mode)


def fill_bar_color(percent):
    if percent > 0.5:
        return "green"
    if 0.5 > percent > 0.2:
        return "yellow"
    if 0.2 > percent:
        return "red"
    # default in case something breaks
    return "gray"


def get_keg_fill_percent(w, cap, tare):
    keg_cap = cap * 1000
    keg_tare = tare * 1000
    net_w = max((w - keg_tare), 0)
    fill_percent = net_w / keg_cap
    return fill_percent


def get_index_from_port(port, hx_list):
    try:
        ports = breakout_ports[port]
    except KeyError:
        return None

    index = None
    for conf in hx_list:
        if conf.get('pd_sck', None) == ports[0] and conf.get('dout', None) == ports[1]:
            index = hx_list.index(conf)
        
    return index


def get_port_from_index(index, hx_list):
    try:
        conf = hx_list[index]
    except IndexError:
        return None

    port = None
    for port_key in breakout_ports.keys():
         if conf.get('pd_sck', None) == breakout_ports[port_key][0] and conf.get('dout', None) == breakout_ports[port_key][1]:
             port = port_key

    return port