"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V /
|  _  ||  _  || ___ \ ___ \ \ /
| | | || | | || |_/ / |_/ / | |
\_| |_/\_| |_/\____/\____/  \_/

Copyright (c) IRSTEA-EDF-AFB 2017-2018

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import os
import cProfile
import pstats
import io

from src.user_preferences_mod import user_preferences


def profileit(func):
    """ Decorator to analyse computational time funtion. Output txt file created in temp folder in user AppData folder.
    For developper, if used (import of this decorator),
    it will recreate/reimport the class and recreate AppData structure. """
    def wrapper(*args, **kwargs):
        path_stat = user_preferences.user_pref_temp_path
        datafn = func.__name__ + ".txt"  # Name the data file sensibly
        prof = cProfile.Profile()
        retval = prof.runcall(func, *args, **kwargs)
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(prof, stream=s).sort_stats(sortby)
        ps.print_stats()
        with open(os.path.join(path_stat, datafn), 'w') as perf_file:
            perf_file.write(s.getvalue())
        return retval

    return wrapper
