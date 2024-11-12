import functools
import os
import pickle
import shutil
import time
from collections import defaultdict

from base4.utilities.common import list_files_in_directory, make_hashable

HDD_MEMOIZE_CACHE_FOLDER = '/tmp/io2cache/memoize'


def memoize(ttl):
    def decorator(func):
        cache = {}
        cache_times = defaultdict(lambda: 0)

        @functools.wraps(func)
        async def wrapped(*args, **kwargs):

            # DISABLE MEMOIZE
            # return await func(*args, **kwargs)

            key = (make_hashable(args), make_hashable(kwargs))
            current_time = time.time()

            # Invalidate cache if TTL has expired
            if key in cache and (current_time - cache_times[key]) > ttl:
                del cache[key]
                del cache_times[key]

            # Return cached value if available and valid
            if key in cache:
                return cache[key]

            # Compute new value and update cache
            result = await func(*args, **kwargs)
            cache[key] = result
            cache_times[key] = current_time
            return result

        return wrapped

    return decorator




def hdd_memoize_clear_cache_folder():
    shutil.rmtree(HDD_MEMOIZE_CACHE_FOLDER, ignore_errors=True)
    os.makedirs(HDD_MEMOIZE_CACHE_FOLDER, exist_ok=True)


def hdd_memoize(ttl):
    def decorator(func):

        global HDD_MEMOIZE_CACHE_FOLDER
        os.makedirs(HDD_MEMOIZE_CACHE_FOLDER, exist_ok=True)

        @functools.wraps(func)
        async def wrapped(*args, **kwargs):

            # DISABLE MEMOIZE
            # return func(*args, **kwargs)

            key = (make_hashable(args), make_hashable(kwargs))

            fname = '_'.join([func.__module__, func.__name__]).replace('.', '_')
            fname += '.' + str(hash(key))

            current_time = int(time.time() * 1000)

            target = HDD_MEMOIZE_CACHE_FOLDER + '/' + f'{fname}.*.pickle'

            cache_files = list_files_in_directory(target)

            for cf in cache_files[::-1]:

                file_in_fname_time = int(cf.split('.')[-2])

                if (current_time - file_in_fname_time) > ttl * 1000:
                    os.unlink(HDD_MEMOIZE_CACHE_FOLDER + '/' + cf)
                    continue
                else:
                    with open(HDD_MEMOIZE_CACHE_FOLDER + '/' + cf, 'rb') as f:
                        return pickle.load(f)

            # Compute new value and update cache
            result = await func(*args, **kwargs)

            try:
                with open(f'{HDD_MEMOIZE_CACHE_FOLDER}/{fname}.{current_time}.pickle', 'wb') as f:
                    pickle.dump(result, f)
            except Exception as e:
                raise

            return result

        return wrapped

    return decorator
