## Sun predictions on a Slack channel

This bot helps you get the Some of the solar magnetic activity
information on your slack channel.

Create a configuration file with the following template:

```
[SUNSLACK]
token: xoxb-123456790-123456790-123456790
channel: sunflux
cachedir: /var/tmp/sunflux
font: /System/Library/Fonts/Supplemental/Arial.ttf
logfile: /tmp/sunflux.log
loglevel: INFO
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
1  *  *  *  *  /usr/local/bin/sunslack --config ~/.sunslack.conf -a -f -m
```

## Example of graphs published

![Flux plot](misc/flux.png)

![MUF plot](misc/MUF.gif)

## Slack Screen Shot

![Slack Screen Shot](misc/Slack-Screenshot.png)

[1]: https://api.slack.com/apps
