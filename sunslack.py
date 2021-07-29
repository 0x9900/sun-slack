#!/usr/bin/env python
#
"""This is a slack bot that read the sun activity predictions from
NOAA, generate a graph and upload the graph on a slack channel.

NOAA updates these data once a days. The a new graph will be generated
only if a new data is available.

"""

__version__ = "1.0.1"

import os

import logging
import pickle
import sys

from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import requests

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

FLUX_URL = "https://services.swpc.noaa.gov/products/summary/10cm-flux.json"
FORECAST_URL = "https://services.swpc.noaa.gov/text/27-day-outlook.txt"
CACHE_DIR = "/tmp/sunslack"

#CHANNEL_ID = 'C01TVLS0RDJ'
CHANNEL_ID = 'sunflux'

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%c',
                    level=logging.INFO)


class Predictions:
  """Data structure storing all the sun indices predictions"""

  date = None
  fields = []

  def __cmp__(self, other):
    return (self.date > other.date) - (self.date < other.date)

  def __eq__(self, other):
    if other is None:
      return False
    return self.date == other.date


class SunRecord:
  """Datastructure holding the sun forecast information"""
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

  def __init__(self, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    cachefile = os.path.join(cache_dir, 'flux.pkl')
    self.data = {}

    cached_data = readcache(cachefile)
    self.data = self.download_flux()

    if self.data == cached_data:
      self.newdata = False
    else:
      self.newdata = True
      writecache(cachefile, self.data)

  @staticmethod
  def download_flux():
    """Download the current measuref 10.7 cm flux index"""
    try:
      req = requests.get(FLUX_URL)
      data = req.json()
    except requests.ConnectionError as err:
      logging.error('Connection error: %s we will try later', err)
      sys.exit(os.EX_IOERR)

    if req.status_code != 200:
      return None

    return dict(flux=int(data['Flux']),
                time=datetime.strptime(data['TimeStamp'], '%Y-%m-%d %H:%M:%S'))

  @property
  def flux(self):
    return self.data['flux']

  @property
  def time(self):
    return self.data['time']


class Forecast:

  def __init__(self, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    cachefile = os.path.join(cache_dir, 'forecast.pkl')
    self.data = None

    cached_data = readcache(cachefile)
    self.data = self.download_forecast()

    if self.data == cached_data:
      self.newdata = False
    else:
      self.newdata = True
      writecache(cachefile, self.data)


  @staticmethod
  def download_forecast():
    """Download the forecast data from noaa"""
    try:
      req = requests.get(FORECAST_URL)
    except requests.ConnectionError as err:
      logging.error('Connection error: %s we will try later', err)
      sys.exit(os.EX_IOERR)


    predictions = Predictions()
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

  @property
  def date(self):
    return self.data.date

  @property
  def fields(self):
    return self.data.fields


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


def plot(predictions, filename):
  """Plot forecast"""
  fields = predictions.fields
  dates = [s.date for s in fields]
  a_index = [s.a_index for s in fields]
  kp_index = [s.kp_index for s in fields]
  flux = [s.flux for s in fields]

  plt.style.use('ggplot')
  fig, ax1 = plt.subplots(figsize=(12, 7))
  fig.suptitle('Solar Activity Predictions for: {} UTC'.format(predictions.date),
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


def main():
  """Everyone needs a main purpose"""
  try:
    with open(os.path.expanduser('~/.slack-token')) as fd_token:
      token = fd_token.readline().strip()
  except FileNotFoundError as err:
    logging.error(err)
    sys.exit(os.EX_OSFILE)

  logging.info("Gathering data")
  forecast = Forecast(CACHE_DIR)
  flux = Flux(CACHE_DIR)
  client = WebClient(token=token)

  if flux.newdata:
    try:
      message = "10.7cm flux index {:d} on {} UTC".format(
        flux.flux, flux.time.strftime("%b %d %H:%M")
      )
      client.chat_postMessage(channel=CHANNEL_ID, text=message)
      logging.info("10cm flux %d on %s", flux.flux, flux.time.strftime("%b %d %H:%M"))
    except SlackApiError as err:
      logging.error("postMessage error: %s", err.response['error'])
  else:
    logging.info('No new message to post')

  if forecast.newdata:
    plot_file = 'flux_{}.png'.format(forecast.date.strftime('%Y%m%d%H%M'))
    plot(forecast, plot_file)
    logging.info('A new plot file %s generated', plot_file)
    try:
      title = 'Previsions for: {}'.format(forecast.date.strftime("%b %d %H:%M"))
      client.files_upload(file=plot_file, channels=CHANNEL_ID, initial_comment=title)
      logging.info("Sending plot file: %s", plot_file)
    except SlackApiError as err:
      logging.error("file_upload error: %s", err.response['error'])
  else:
    logging.info('No new graph to post')


if __name__ == "__main__":
  main()
