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
1  *  *  *  *  /usr/local/bin/sunslack --config ~/.sunslack.conf -a -f -m >/dev/null
```

## Example of graphs published

![Flux plot](misc/flux.png)

![MUF plot](misc/MUF.gif)

[1]: https://api.slack.com/apps
