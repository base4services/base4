loaded = False


def load_dotenv(print_check: bool = True):
    global loaded

    if loaded:
        return

    from base4.utilities.files import env
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=env())

    if print_check:
        print(env(),'file loaded')

    loaded=True