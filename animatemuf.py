#!/usr/bin/env python3

import argparse
import json
import logging
import os
import re
import sys

from subprocess import Popen, PIPE

from urllib.request import urlretrieve
from datetime import datetime, timedelta

from PIL import Image, ImageFont, ImageDraw

from sunslack import read_config

NOAA = "https://services.swpc.noaa.gov/experimental"
SOURCE_JSON = NOAA + "/products/animations/ctipe_muf.json"

logging.basicConfig(level=logging.INFO)

RE_TIME = re.compile(r'.*_(\d+T\d+).png').match

def extract_time(name):
  str_time = RE_TIME(name).group(1)
  return datetime.strptime(str_time, '%Y%m%dT%H%M%S')

def retreive_files(config):
  urlretrieve(SOURCE_JSON, config.muf_file)
  with open(config.muf_file, 'r', encoding='utf-8') as fdin:
    data_source = json.load(fdin)
    for url in data_source:
      filename = os.path.basename(url['url'])
      target_name = os.path.join(config.target_dir, filename)
      if os.path.exists(target_name):
        continue
      logging.info('%s saved', target_name)
      urlretrieve(NOAA + url['url'], target_name)

def cleanup(config):
  logging.info('Cleaning up old MUF images')
  expire_time = datetime.utcnow() - timedelta(days=1, hours=12)
  for name in os.listdir(config.target_dir):
    if not name.startswith('CTIPe-MUF'):
      continue
    try:
      file_d = extract_time(name)
      if file_d < expire_time:
        os.unlink(os.path.join(config.target_dir, name))
        logging.info('Delete file: %s', name)
    except IOError as err:
      logging.error(err)

def animate(config):
  # image sizes (1290, 700) (640, 400) (800, 600)
  font = ImageFont.truetype(config.font, int(config.font_size))
  animation = os.path.join(config.target_dir, 'muf.gif')
  image_list = []

  file_list = []
  for name in sorted(os.listdir(config.target_dir)):
    if not name.startswith('CTIPe-MUF_'):
      continue
    file_list.append(name)

  logging.info('Processing: %d images', len(file_list))
  for name in file_list:
    fullname = os.path.join(config.target_dir, name)
    logging.debug('Add %s', name)
    image = Image.open(fullname)
    image = image.convert('RGB')
    image = image.resize((800, 600), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    draw.text((25, 555), "W6BSD - MUF 36 hours animation", font=font, fill="gray")
    image_list.append(image)

  if len(image_list) > 2:
    logging.info('Saving animation into %s', animation)
    image_list[0].save(animation, save_all=True, optimize=True, duration=75,
                       loop=0, append_images=image_list[1:])
  else:
    logging.info('Nothing to animate')

def gen_video(config):
  logfile = os.path.join(config.target_dir, 'muf.log')
  gif_file = os.path.join(config.target_dir, 'muf.gif')

  if not os.path.isfile(config.converter):
    logging.error('Video converter %s not found', config.converter)
    return

  cmd = f'{config.converter} {gif_file} {config.video_file}'
  with open(logfile, "w") as err:
    print(cmd, file=err)
    proc = Popen(cmd.split(), shell=False, stdout=PIPE, stderr=err)
  logging.info(f"Saving %s video file", config.video_file)
  proc.wait()
  if proc.returncode != 0:
    logging.error('Error generating the video file. Status code: %d', proc.returncode)

def main(args=sys.argv[:1]):
  parser = argparse.ArgumentParser(description='MUF animation')
  parser.add_argument("--config", type=str, required=True,
                      help="configuration file path")
  parser.add_argument('-v', '--no-video', action='store_false', default=True,
                      help='Produce an mp4 video')
  opts = parser.parse_args()
  _config = read_config(os.path.expanduser(opts.config))
  config = _config['animatemuf']
  del _config

  if not os.path.isdir(config.target_dir):
    logging.error("The target directory %s does not exist", config.target_dir)
    return

  retreive_files(config)
  cleanup(config)
  if opts.no_video:
    animate(config)
    gen_video(config)


if __name__ == "__main__":
  main()
