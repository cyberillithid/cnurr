# CNURR — Crawler for old EtherPad/Piratenpad

**CNURR** is an automated crawler for backing up your team pads in old EtherPad.

As of now, more and more servers hosting [old EtherPad](https://github.com/ether/pad) decide to shut it down due to well-known performance and security problems.

## Usage

You can use it from commandline or by writing your `input.txt`.

My `input.txt` looks like:

```sh
# Domains
-t user@name.com password https://domain.titanpad.com
-a -f -t user@name.com password https://domain.piratenpad.de
# Standalone pads
-r http://sync.in pad_1
https://teams.piratenpad.de pad_2 pad_3
```

`python cnurr.py -h` shows you help.

## SAQ (Supposedly Askable Questions)

**Why would I want to back it up using this tool, if there is standard export tool?**

Default export of old EtherPad completely misses the changes and, most importantly, author data.

**What of passworded pads?**

I'm not totally sure, but it looks that either entered password is connected to the username, not the cookie set, or that admin access to the 'restore pad' somehow circumvents password requirements.
