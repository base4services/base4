from base4.utilities.contants import BaseEnum

class Lookup(BaseEnum):
    MINUTE = 60
    HOUR = 60 * 60
    DAY = 60 * 60 * 24
    MONTH = 60 * 60 * 24 * 30
    YEAR = 60 * 60 * 24 * 30 * 12
