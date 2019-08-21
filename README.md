![intensify.pictures](/static/intensify-logo.gif)

[intensification as a service intensifies]

See https://intensify.pictures for demo.

Hacking
=======

Presently there's no setup.py or tests because I'm lazy.
Right now the only supported environment is Debian Buster (but most recent Linuxes should work, including Ubuntu running under Windows Subsystem for Linux).

To hack, first install prereqs: `sudo apt install python3-flask python3-pil gifsicle`

Then you can make output dirs and start a dev server: `mkdir uploads intensified; FLASK_ENV=development flask run`
