import os


def ifbreakpoint():

    if os.getenv('debug', None) in ('true', '1', 'yes'):
        breakpoint()
