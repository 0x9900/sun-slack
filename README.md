## Sun predictions on a Slack channel

This bot helps you get the Some of the solar magnetic activity
information on your slack channel.

Create a configuration file with the following template:

```
[SUNSLACK]
token: xoxb-123456790-123456790-123456790
channel: sunflux
cachedir: /var/tmp/sunflux
loglevel: INFO
[ANIMATEMUF]
target_dir: /var/tmp/muf
converter: /usr/local/bin/convert.sh
muf_file: /tmp/muf_source.json
video_file: /tmp/muf/muf.mp4
font: /System/Library/Fonts/Supplemental/Arial Narrow.ttf
font_size: 16
```

You can get a token for your bot by registering it on the [Slack
App][1] website.

The field `font` is the path the the font that will be used in the MUF
animated image.

If you are running the program `sunflux` in cron, it is a good idea to
specifying in a logfile name.

You can run the bot every hour in cron. It only sends messages and
upload the prediction graph when NOAA publishes new data.

Line to add in your crontab:
```
1 * * * * /usr/local/bin/sunslack --config ~/.sslack.cnf --alerts --flux --muf
```

## Example of graphs published

![Flux plot](misc/flux.png)

## Slack Screen Shot

![Slack Screen Shot](misc/Slack-Screenshot.png)

[1]: https://api.slack.com/apps
