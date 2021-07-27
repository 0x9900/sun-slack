#!/usr/bin/env python
#
import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import requests
import logging

from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

FLUX_URL = "https://services.swpc.noaa.gov/products/summary/10cm-flux.json"
FORECAST_URL = "https://services.swpc.noaa.gov/text/27-day-outlook.txt"

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%c',
                    level=logging.INFO)

class Predictions:
    date = None
    fields = []

class SunRecord(object):
  """Datastructure holding the sum forecast information"""

  __slot__ = ["date", "flux", "a_index", "kp_index"]

  def __init__(self, args):
    date = datetime.strptime('{} {} {}'.format(*args[0:3]), "%Y %b %d")
    setattr(self, 'date', date)
    setattr(self, 'flux', int(args[3]))
    setattr(self, 'a_index', int(args[4]))
    setattr(self, 'kp_index', int(args[5]))

  def __repr__(self):
    return '{} [{}]'.format(self.__class__, ' '.join('%s: %s' % (k, getattr(self, k)) for k in self.__slot__))

  def __str__(self):
     return "{0.date} {0.flux} {0.a_index} {0.kp_index}".format(self)


def download_flux():
  """Download the current measuref 10.7 cm flux index"""
  try:
    req = requests.get(FLUX_URL)
  except requests.ConnectionError as err:
    logging.error('Connection error: %s we will try later', err)
    sys.exit(os.EX_IOERR)

  if req.status_code != 200:
    return None

  data = req.json()
  return dict(flux=int(data['Flux']),
              time=datetime.strptime(data['TimeStamp'], '%Y-%m-%d %H:%M:%S'))


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


def plot(predictions, filename):
  """Plot forecast"""
  fields = predictions.fields
  dates = [s.date for s in fields]
  a_index = np.array([s.a_index for s in fields])
  kp_index = np.array([s.kp_index for s in fields])
  flux = np.array([s.flux for s in fields])

  plt.style.use('ggplot')
  fig, ax = plt.subplots(figsize=(12, 7))
  fig.suptitle('Solar Activity Predictions for: {} UTC'.format(predictions.date),
               fontsize=16)
  fig.text(.02, .05, 'http://github.com/0x9900/sun-slack', rotation=90)

  # first axis
  ax.plot(dates, a_index, ":b", label='A-index')
  ax.plot(dates, kp_index, "--m", label='KP-index')
  ax.set_ylabel('Index', fontweight='bold')
  ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
  ax.xaxis.set_tick_params(rotation=45, labelsize=10)
  ax.grid(True)

  # second axis
  ax2 = ax.twinx()
  ax2.plot(dates, flux, "r", label='Flux')
  ax2.set_ylim([flux.min()-10, flux.max()+3])
  ax2.set_ylabel('Flux', fontweight='bold')
  ax2.grid(False)
  fig.legend(loc='upper right', bbox_to_anchor=(0.25, 0.85))

  plt.savefig(filename, transparent=False, dpi=100)


def main():
  """Everyone needs a main purpose"""
  forecast = download_forecast()
  current_flux = download_flux()
  new_plot = False

  try:
    with open(os.path.expanduser('~/.slack-token')) as fd_token:
      token = fd_token.readline().strip()
    client = WebClient(token=token)
  except FileNotFoundError as err:
    logging.error(err)
    sys.exit(os.EX_OSFILE)

  plot_file = 'flux-{}.png'.format(forecast.date.strftime('%Y%m%d-%H%M'))
  if not os.path.exists(plot_file):
    plot(forecast, plot_file)
    logging.info('A new plot file %s generated', plot_file)
    new_plot = True

  if current_flux:
    try:
      message = "Current 10.7cm flux index {:d} at {}".format(
        current_flux['flux'], current_flux['time'].strftime("%H:%M")
      )
      response = client.chat_postMessage(channel="#sunflux", text=message)
      logging.info("Current 10cm flux %d at %s", current_flux['flux'], current_flux['time'])
    except SlackApiError as e:
      logging.error("postMessage error: %s", e.response['error'])

  if new_plot:
    try:
      response = client.files_upload(channel='#sunflux', file=plot_file)
      logging.info("Sending plot file: %s", plot_file)
    except SlackApiError as e:
      logging.error("file_upload error: %s", e.response['error'])


if __name__ == "__main__":
  main()
