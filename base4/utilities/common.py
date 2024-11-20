import glob
import math
import os
import importlib
import bcrypt


def hash_password(password):
    if os.getenv('TEST_MODE') == 'true':
        return password
    _salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), _salt)
    return hashed_password.decode('utf-8')


def check_hashed_password(password, hashed_password):
    if os.getenv('TEST_MODE') == 'true':
        return password == hashed_password
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def make_hashable(obj):
    """Convert an object to a hashable type"""
    if isinstance(obj, (tuple, list)):
        return tuple((make_hashable(e) for e in obj))
    if isinstance(obj, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
    return obj


def list_files_in_directory(search_pattern):
    return [os.path.basename(file) for file in glob.glob(search_pattern) if os.path.isfile(file)]


nonworking_days = {
    2024: {
        "2024-01-01": {"holiday": {"it": "Capodanno", "de": "Neujahr", "sr": "Nova godina", "en": "New Year's Day", "nonworking": ["it", "de", "sr"]}},
        "2024-01-06": {
            "holiday": {"it": "Epifania", "de": "Heilige Drei Könige", "sr": "Badnje veče", "en": "Epiphany / Orthodox Christmas Eve", "nonworking": ["sr"]}
        },
        "2024-01-07": {"holiday": {"it": "Natale Ortodosso", "de": "Orthodoxe Weihnachten", "sr": "Božić", "en": "Orthodox Christmas", "nonworking": ["sr"]}},
        "2024-01-14": {
            "holiday": {
                "it": "Capodanno Ortodosso",
                "de": "Orthodoxes Neujahr",
                "sr": "Pravoslavna Nova godina",
                "en": "Orthodox New Year",
                "nonworking": ["sr"],
            }
        },
        "2024-02-15": {
            "holiday": {
                "it": "Giorno della Stato Serbo",
                "de": "Serbischer Staatsfeiertag",
                "sr": "Dan državnosti Srbije",
                "en": "Serbia Statehood Day",
                "nonworking": ["sr"],
            }
        },
        "2024-02-16": {
            "holiday": {
                "it": "Giorno della Stato Serbo",
                "de": "Serbischer Staatsfeiertag",
                "sr": "Dan državnosti Srbije",
                "en": "Serbia Statehood Day",
                "nonworking": ["sr"],
            }
        },
        "2024-03-31": {"holiday": {"it": "Pasqua", "de": "Ostern", "sr": "Uskrs", "en": "Easter", "nonworking": ["it", "de"]}},
        "2024-04-01": {
            "holiday": {"it": "Lunedì dell'Angelo", "de": "Ostermontag", "sr": "Uskršnji ponedeljak", "en": "Easter Monday", "nonworking": ["it", "de"]}
        },
        "2024-04-05": {
            "holiday": {
                "it": "Venerdì Santo Ortodosso",
                "de": "Orthodoxer Karfreitag",
                "sr": "Veliki petak",
                "en": "Orthodox Good Friday",
                "nonworking": ["sr"],
            }
        },
        "2024-04-07": {"holiday": {"it": "Pasqua Ortodossa", "de": "Orthodoxes Ostern", "sr": "Vaskrs", "en": "Orthodox Easter", "nonworking": ["sr"]}},
        "2024-04-08": {
            "holiday": {
                "it": "Lunedì di Pasqua Ortodossa",
                "de": "Orthodoxer Ostermontag",
                "sr": "Vaskršnji ponedeljak",
                "en": "Orthodox Easter Monday",
                "nonworking": ["sr"],
            }
        },
        "2024-04-25": {
            "holiday": {"it": "Festa della Liberazione", "de": "Tag der Befreiung", "sr": "Dan oslobođenja", "en": "Liberation Day", "nonworking": ["it"]}
        },
        "2024-05-01": {
            "holiday": {"it": "Festa dei Lavoratori", "de": "Tag der Arbeit", "sr": "Praznik rada", "en": "Labour Day", "nonworking": ["it", "de", "sr"]}
        },
        "2024-05-09": {"holiday": {"it": "Ascensione", "de": "Christi Himmelfahrt", "sr": "Spasovdan", "en": "Ascension Day", "nonworking": ["de", "sr"]}},
        "2024-05-19": {"holiday": {"it": "Pentecoste", "de": "Pfingsten", "sr": "Duhovi", "en": "Pentecost", "nonworking": ["it", "de"]}},
        "2024-05-20": {
            "holiday": {"it": "Lunedì di Pentecoste", "de": "Pfingstmontag", "sr": "Duhovski ponedeljak", "en": "Whit Monday", "nonworking": ["de"]}
        },
        "2024-06-02": {
            "holiday": {"it": "Festa della Repubblica", "de": "Tag der Republik", "sr": "Dan Republike", "en": "Republic Day", "nonworking": ["it"]}
        },
        "2024-06-20": {"holiday": {"it": "Corpus Domini", "de": "Fronleichnam", "sr": "Tijelovo", "en": "Corpus Christi", "nonworking": ["de"]}},
        "2024-06-28": {"holiday": {"it": "Vidovdan", "de": "Vidovdan", "sr": "Vidovdan", "en": "St. Vitus Day", "nonworking": ["sr"]}},
        "2024-08-15": {
            "holiday": {"it": "Ferragosto", "de": "Mariä Himmelfahrt", "sr": "Velika Gospojina", "en": "Assumption of Mary", "nonworking": ["it", "de"]}
        },
        "2024-11-01": {"holiday": {"it": "Ognissanti", "de": "Allerheiligen", "sr": "Svi Sveti", "en": "All Saints' Day", "nonworking": ["it", "de"]}},
        "2024-12-08": {
            "holiday": {
                "it": "Immacolata Concezione",
                "de": "Mariä Empfängnis",
                "sr": "Bezgrešno Začeće",
                "en": "Immaculate Conception",
                "nonworking": ["it", "de"],
            }
        },
        "2024-12-25": {"holiday": {"it": "Natale", "de": "Weihnachten", "sr": "Božić", "en": "Christmas", "nonworking": ["it", "de", "sr"]}},
        "2024-12-26": {"holiday": {"it": "Santo Stefano", "de": "Stephanstag", "sr": "Sveti Stefan", "en": "St. Stephen's Day", "nonworking": ["it", "de"]}},
    }
}


def hhmm(float_time: float) -> str:
    hh = math.floor(float_time)
    mm = math.floor((float_time - hh) * 60)
    return f'{hh:02d}:{mm:02d}'


def format_duration(seconds):
    # Define time units in seconds
    units_years = [('year', 60 * 60 * 24 * 365)]
    units_months = [('month', 60 * 60 * 24 * 30)]
    units_weeks = [('week', 60 * 60 * 24 * 7)]
    units_days = [('day', 60 * 60 * 24)]
    units_hours = [('h', 60 * 60)]
    units_minutes = [('min', 60)]
    units_seconds = [('sec', 1)]

    if not seconds:
        return "0 sec"

    try:
        result = []

        # Check if time is less than 1 hour
        if seconds < 60 * 60:
            units = units_minutes + units_seconds

        # Check if time is between 1 hour and 24 hours
        elif seconds < 60 * 60 * 24:
            units = units_hours + units_minutes

        # Check if time is between 24 hours and 7 days
        elif seconds < 60 * 60 * 24 * 7:
            units = units_days + units_hours

        # Check if time is between 7 days and 4 weeks
        elif seconds < 60 * 60 * 24 * 7 * 4:
            units = units_weeks + units_days + units_hours

        # Check if time is between 4 weeks and 52 weeks (1 year)
        elif seconds < 60 * 60 * 24 * 7 * 52:
            units = units_months + units_weeks + units_days

        # If time is greater than or equal to 1 year
        else:
            units = units_years + units_months + units_days

        # Loop over the units and calculate how many of each are in the given seconds
        for unit_name, unit_seconds in units:
            if seconds >= unit_seconds:
                unit_value = seconds // unit_seconds
                seconds %= unit_seconds
                if unit_value > 0:
                    # Handle pluralization (e.g., "1 day" vs "2 days")
                    if unit_value == 1:
                        result.append(f"1 {unit_name}")
                    else:
                        result.append(f"{int(unit_value)} {unit_name}s")

        # Join the result parts
        return ' '.join(result)
    except Exception as e:
        raise


def old_format_duration(seconds):
    # Define time units in seconds
    units = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('week', 60 * 60 * 24 * 7),
        ('day', 60 * 60 * 24),
        ('h', 60 * 60),
        ('min', 60),
        ('sec', 1),
    ]

    if not seconds:
        return 0
    try:
        result = []

        # Loop over the units and calculate how many of each are in the given seconds
        for unit_name, unit_seconds in units:
            if seconds >= unit_seconds:
                unit_value = seconds // unit_seconds
                seconds %= unit_seconds
                if unit_value > 0:
                    result.append(f"{unit_value} {unit_name}")

        # Join the result parts
        return ' '.join(result)
    except Exception as e:
        raise


def split_list(input_list, m):
    full_lists_count = len(input_list) // m

    split_lists = [input_list[i * m : (i + 1) * m] for i in range(full_lists_count)]

    remainder = len(input_list) % m
    if remainder:
        split_lists.append(input_list[full_lists_count * m :])

    return split_lists


    
def import_all_from_dir(directory: str, package: str):
    """
    Dinamički uvozi sve simbole iz svih .py fajlova u datom direktorijumu.

    :param directory: Putanja do direktorijuma gde se nalaze moduli.
    :param package: Ime paketa za uvoz (koristi se za relativni import).
    """
    # Prostor imena u koji ćemo dodavati simbole
    global_namespace = globals()
    
    # Iteracija kroz fajlove u datom direktorijumu
    for file_name in os.listdir(directory):
        # Ignoriši '__init__.py' i fajlove koji nisu Python moduli
        if file_name.endswith(".py") and file_name != "__init__.py":
            module_name = file_name[:-3]  # Uklanjanje ekstenzije '.py'
            module = importlib.import_module(f".{module_name}", package=package)
            
            # Dodavanje simbola iz modula u globalni prostor
            if hasattr(module, "__all__"):
                # Ako modul ima definisan __all__, uvozi samo te simbole
                for symbol in module.__all__:
                    global_namespace[symbol] = getattr(module, symbol)
            else:
                # Ako nema __all__, uvozi sve simbole koji ne počinju sa "_"
                for symbol in dir(module):
                    if not symbol.startswith("_"):
                        global_namespace[symbol] = getattr(module, symbol)
