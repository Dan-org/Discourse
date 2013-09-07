Overview
====================

Discourse is a general Django app currently in the early stages of development for content and communication.  
It acts as the filler of the website, without defining the basic functionality.

It adds the following capabilities:

- Comment System
- Content Editing and Organization (wiki like content editing of structured content)
- Media Library (media uploads as attachment's to objects)
- Calendar System (gleens support)
- Event Stream System (like a facebook or twitter feed)



Installation
-------------------
Prerequisites for Mac OS:
Make sure you have the XCode development environment and the Development Command Line Tools.  They can be downloaded from https://developer.apple.com/downloads/index.action, you need Xcode 4.6 or higher, and "Command Line Tools" for your version of your OS.

Prerequisites for Linux:
Make sure you have python 2.6 or higher installed (it should be).  You can check by running "python" and looking at the first line.  Also make sure you have python-setuptools by seeing if the command "easy_install" is available.  If that command fails to run, try going to http://pypi.python.org/pypi/setuptools

Step 1:
Make sure you have pip and virtualenv installed by doing:

  > sudo easy_install pip virtualenv
  ...
  Finished processing dependencies for virtualenv

Step 2:
In the project root, create a python virtual environment named "env".

  > virtualenv env
  New python executable in env/bin/python
  Installing setuptools............done.
  Installing pip...............done.


Step 3:
Install the project requirements.  Make sure you see "Successfully installed ..." at the end.  Otherwise check troubleshooting, below.

  > env/bin/pip install -r requirements.txt
  ...
  Successfully installed Django
  Cleaning up...

Step 4:

  > ./manage.py syncdb
  Ceating tables ...
  ...
  Would you like to create one now? (yes/no):

It will ask you to create a user, go ahead and create one for yourself.  That user will only be local to *your* machine so don't expect it to be anywhere else.  If this fails, or you want to create a user later see "Creating An Admin User Via The Command Line", below.  Also, there is by default a user with email "admin@designforamerica.com" and password "pass".

Step 5:
Load test data

> ./manage.py loaddata example/fixtures/test.json

Step 6:
  
  > ./manage.py runserver
  ...
  Development server is running at http://127.0.0.1:8000/
  Quit the server with CONTROL-C.

This will start up the server, running.  Visit http://127.0.0.1:8000/ in your browser now.
Changes you make should automatically update the server, but if sometimes it needs to be rebooted.
