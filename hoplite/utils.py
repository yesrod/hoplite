import sys

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