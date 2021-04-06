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
import ssl
import urllib.request as urllib


def get_last_version_number_from_github():
    """Return the last version of HABBY solfware from github master tags."""
    last_version_str = "unknown"
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        url_github = 'https://api.github.com/repos/YannIrstea/habby/tags'
        with urllib.urlopen(url_github) as response:
            html = response.read()
            last_version_str = eval(html)[0]["name"][1:]
    except:
        print("Warning: No internet access to get last software version.")

    return last_version_str