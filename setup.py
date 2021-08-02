#!/usr/bin/env python3
#
import sys

from setuptools import setup, find_packages

import sunslack

__doc__ = """
## Sun predictions on a Slack channel

This bot helps you get the Some of the solar magnetic activity
information on your slack channel.

Create a configuration file with the following template:

```
[SUNSLACK]
token: xoxb-123456790-123456790-123456790
channel: sunflux
cachedir: /var/tmp/sunflux
```

You can get a token for your bot by registering it on the [Slack
App][1] website.

You can run the bot every hour in cron. It only sends messages and
upload the prediction graph when NOAA publishes new data.

Line to add in your crontab:
```
1  *  *  *  *  /usr/local/bin/sunslack --config ~/.sunslack.conf >/dev/null
```


[1]: https://api.slack.com/apps

"""

__author__ = "Fred C. (W6BSD)"
__version__ = sunslack.__version__
__license__ = 'BSD'

URLS = {
  'Source': 'https://github.com/0x9900/sun-slack/',
  'Tracker': 'https://github.com/0x9900/sun-slack/issues',
}

py_version = sys.version_info[:2]
if py_version < (3, 6):
  raise RuntimeError('sun-slack requires Python 3.6 or later')

setup(
  name='sunslack',
  version=__version__,
  description='Slack bot publishing NOAA Solar data',
  long_description=__doc__,
  long_description_content_type='text/markdown',
  url='https://0x9900.com/',
  project_urls = URLS,
  license=__license__,
  author=__author__,
  author_email='w6bsd@bsdworld.org',
  py_modules=['sunslack'],
  python_requires=">=3.6.0",
  install_requires=['matplotlib', 'slack_sdk'],
  entry_points = {
    'console_scripts': ['sunslack = sunslack:main'],
  },
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Topic :: Communications :: Ham Radio',
  ],
)
