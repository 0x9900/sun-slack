#!/usr/bin/env python
#
# pylint: disable=C0116

"""This is a slack bot that read the sun activity predictions from
NOAA, generate a graph and upload the graph on a slack channel.

NOAA updates these data once a days. The a new graph will be generated
only if a new data is available.

"""

__version__ = "1.1.8"

import argparse
import logging
import os
import pickle
import sys

from collections import defaultdict
from configparser import ConfigParser, NoOptionError
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import requests

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

NOAA_URL = 'https://services.swpc.noaa.gov'
ALERTS_URL = NOAA_URL + "/text/wwv.txt"
FLUX_URL = NOAA_URL + "/text/27-day-outlook.txt"

CACHE_DIR = "/tmp/sunslack-data"

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%c', level=logging.INFO)


def read_config(config_file):
  """Sunslack configuration example:
  [SUNSLACK]
  token: xoxb-123456789-123456789
  channel: sunflux
  cachedir: /tmp/sunflux-data
  [ANIMATEMUF]
  target_dir = '/tmp/muf'
  video_file = '/tmp/muf/muf.mp4'
  converter = '/usr/local/bin/convert.sh'
  muf_file = '/tmp/muf_source.json'
  """

  _data = defaultdict(dict)
  parser = ConfigParser()

  if not os.path.exists(config_file):
    logging.error('Configuration file "%s" not found', config_file)
    sys.exit(os.EX_CONFIG)

  with open(config_file, 'r') as fdc:
    parser.read_file(fdc)

  for name, sec in parser.items():
    for key, value in sec.items():
      _data[name.lower()][key] = value

  data = {}
  for name in _data:
    data[name] = type('Config', (object, ), _data[name])
  return data

class NoaaData:
  """Data structure storing all the sun indices predictions"""

  def __init__(self):
    self.date = None
    self.fields = []

  def __cmp__(self, other):
    return (self.date > other.date) - (self.date < other.date)

  def __eq__(self, other):
    if other is None:
      return False
    return self.date == other.date


class SunRecord:
  """Datastructure holding the sun Flux information"""
  __slots__ = ("date", "data")

  def __init__(self, args):
    self.date = datetime.strptime('{} {} {}'.format(*args[0:3]), "%Y %b %d")
    self.data = {}
    self.data['flux'] = int(args[3])
    self.data['a_index'] = int(args[4])
    self.data['kp_index'] = int(args[5])

  def __repr__(self):
    info = ' '.join('%s: %s' % (k, v) for k, v  in self.data.items())
    return '{} [{}]'.format(self.__class__, info)

  def __str__(self):
    return "{0.date} {0.flux} {0.a_index} {0.kp_index}".format(self)

  @property
  def flux(self):
    return self.data['flux']

  @property
  def a_index(self):
    return self.data['a_index']

  @property
  def kp_index(self):
    return self.data['kp_index']


class Flux:
  """The 27-day Space Weather Outlook Table is issued Mondays by 1500 UTC"""

  def __init__(self, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    cachefile = os.path.join(cache_dir, 'flux.pkl')
    self.data = None

    cached_data = readcache(cachefile)
    self.data = self.download_flux()

    if self.data == cached_data:
      self.newdata = False
    else:
      self.newdata = True
      writecache(cachefile, self.data)


  @staticmethod
  def download_flux():
    """Download the flux data from noaa"""
    try:
      req = requests.get(FLUX_URL)
    except requests.ConnectionError as err:
      logging.error('Connection error: %s we will try later', err)
      sys.exit(os.EX_IOERR)

    predictions = NoaaData()
    if req.status_code == 200:
      for line in req.text.splitlines():
        line = line.strip()
        if line.startswith(':Issued:'):
          predictions.date = datetime.strptime(line, ':Issued: %Y %b %d %H%M %Z')
          continue
        if not line or line.startswith(":") or line.startswith("#"):
          continue
        predictions.fields.append(SunRecord(line.split()))
    return predictions

  def __repr__(self):
    return "<{}> at: {}".format(self.__class__.__name__, self.time.isoformat())

  @property
  def time(self):
    return self.data.date

  @property
  def fields(self):
    return self.data.fields


class Alerts:
  """NOAA space weather alerts"""

  def __init__(self, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    cachefile = os.path.join(cache_dir, 'alerts.pkl')
    self.data = None

    cached_data = readcache(cachefile)
    self.data = self.download()

    if self.data == cached_data:
      self.newdata = False
    else:
      self.newdata = True
      writecache(cachefile, self.data)

  @staticmethod
  def download():
    try:
      req = requests.get(ALERTS_URL)
    except requests.ConnectionError as err:
      logging.error('Connection error: %s we will try later', err)
      sys.exit(os.EX_IOERR)

    alerts = NoaaData()
    if req.status_code == 200:
      for line in req.text.splitlines():
        line = line.strip()
        if line.startswith(':Issued'):
          alerts.date = datetime.strptime(line, ':Issued: %Y %b %d %H%M %Z')
          continue
        if not line or line.startswith(':') or line.startswith('#'):
          continue
        alerts.fields.append(line)

    return alerts

  def __repr__(self):
    return "<{}> at: {}".format(self.__class__.__name__, self.time.isoformat())

  @property
  def time(self):
    return self.data.date

  @property
  def text(self):
    return '\n'.join(f for f in self.data.fields if not f.startswith('No space weather'))


def readcache(cachefile):
  """Read data from the cache"""
  try:
    with open(cachefile, 'rb') as fd_cache:
      data = pickle.load(fd_cache)
  except (FileNotFoundError, EOFError):
    data = None
  return data


def writecache(cachefile, data):
  """Write data into the cachefile"""
  with open(cachefile, 'wb') as fd_cache:
    pickle.dump(data, fd_cache)


def download_image(file_name, dest):
  url = NOAA_URL + file_name
  local_name = os.path.join(dest, os.path.basename(file_name))
  if os.path.exists(local_name):
    return (False, local_name)
  logging.debug('Downloading: %s', local_name)
  with requests.get(url, stream=True) as req:
    req.raise_for_status()
    with open(local_name, 'wb') as fout:
      for chunk in req.iter_content(chunk_size=8192):
        fout.write(chunk)
  return (True, local_name)


def plot(predictions, filename):
  """Plot flux"""
  fields = predictions.fields
  dates = [s.date for s in fields]
  a_index = [s.a_index for s in fields]
  kp_index = [s.kp_index for s in fields]
  flux = [s.flux for s in fields]

  plt.style.use('ggplot')
  fig, ax1 = plt.subplots(figsize=(12, 7))
  fig.suptitle('Solar Activity Predictions for: {} UTC'.format(predictions.time),
               fontsize=16)
  fig.text(.02, .05, 'http://github.com/0x9900/sun-slack', rotation=90)

  # first axis
  ax1.plot(dates, a_index, ":b", label='A-index')
  ax1.plot(dates, kp_index, "--m", label='KP-index')
  ax1.set_ylabel('Index', fontweight='bold')
  ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
  ax1.xaxis.set_tick_params(rotation=45, labelsize=10)
  ax1.grid(True)

  # second axis
  ax2 = ax1.twinx()
  ax2.plot(dates, flux, "r", label='Flux')
  ax2.set_ylim([min(flux)-10, max(flux)+3])
  ax2.set_ylabel('Flux', fontweight='bold')
  ax2.grid(False)
  fig.legend(loc='upper right', bbox_to_anchor=(0.25, 0.85))

  plt.savefig(filename, transparent=False, dpi=100)


def yesno(parg):
  yes_strings = ["y", "yes", "true", "1", "on"]
  no_strings = ["n", "no", "false", "0", "off"]
  if parg.lower() in yes_strings:
    return True
  if parg.lower() in no_strings:
    return False
  raise argparse.ArgumentError


def get_alerts(cachedir, channel, client):
  alerts = Alerts(cachedir)
  if not alerts.newdata:
    logging.info('No new Alert message to post')
    return

  try:
    message = []
    message.append("```" + alerts.text + "```")
    message.append("For more information on the sun activity: https://www.swpc.noaa.gov/communities/space-weather-enthusiasts")
    client.chat_postMessage(channel=channel, text='\n'.join(message))
    logging.info("Alerts messages on %s", alerts.time.strftime("%b %d %H:%M"))
  except SlackApiError as err:
    logging.error("postMessage error: %s", err.response['error'])


def get_flux(cachedir, channel, client):
  flux = Flux(cachedir)
  if not flux.newdata:
    logging.info('No new flux graph to post')
    return

  time_tag = datetime.now().strftime('%Y%m%d%H%M')
  plot_file = 'flux_{}.png'.format(time_tag)
  plot_path = os.path.join(cachedir, plot_file)
  plot(flux, plot_path)
  logging.info('A new plot file %s generated', plot_file)
  try:
    title = 'Previsions for: {}'.format(flux.time.strftime("%b %d %H:%M"))
    client.files_upload(file=plot_path, channels=channel, initial_comment=title)
    logging.info("Sending plot file: %s", plot_path)
  except SlackApiError as err:
    logging.error("file_upload error: %s", err.response['error'])


def get_muf(muf_video, channel, client):
  if not os.path.exists(muf_video):
    logging.error("Video file not found: %s", muf_video)
    return
  try:
    title = "MUF for the last 24 hours _click on the image to see the animation_"
    client.files_upload(file=muf_video, channels=channel, initial_comment=title)
    logging.info("Sending muf animation file: %s", muf_video)
  except SlackApiError as err:
    logging.error("file_upload error: %s", err.response['error'])


def main():
  # pylint: disable=too-many-statements
  """Everyone needs a main purpose"""

  parser = argparse.ArgumentParser(description="Send NOAA sun predictions to slack")
  parser.add_argument("--config", type=str, required=True,
                      help="configuration file path")
  parser.add_argument("-a", "--alerts", action='store_true',
                      help="Alerts messages from NOAA (yes/no) [default: %(default)s]")
  parser.add_argument("-f", "--flux", action='store_true',
                      help=("Flux, Aindex, Kpindex weekly previsions (yes/no)"
                            " [default: %(default)s]"))
  parser.add_argument("-m", "--muf", action='store_true',
                      help="MUF previsions map (yes/no) [default: %(default)s]")
  opts = parser.parse_args()
  _config = read_config(os.path.expanduser(opts.config))
  config = _config['sunslack']
  anim_conf = _config['animatemuf']
  del _config

  logger = logging.getLogger()
  if config.loglevel != logger.level:
    logger.setLevel(config.loglevel)

  client = WebClient(token=config.token)

  if not any([opts.alerts, opts.flux, opts.muf]):
    logging.warning('Please select [--alerts, --flux, --muf]. Multiple selections are ok')
    return

  if opts.alerts:
    get_alerts(config.cachedir, config.channel, client)
  if opts.flux:
    get_flux(config.cachedir, config.channel, client)
  if opts.muf:
    get_muf(anim_conf.video_file, config.channel, client)


if __name__ == "__main__":
  main()
