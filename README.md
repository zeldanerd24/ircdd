IRC Distributed Daemon
=====
[![Build Status](https://travis-ci.org/kzvezdarov/ircdd.svg)](https://travis-ci.org/kzvezdarov/ircdd)

* License: GNU GPL v3. See LICENSE for details
* Source: `github.com/kzvezdarov/ircdd`

IRCDD is a simple distributed IRC daemon.

# Testing
## Testing on Vagrant
The repository contains a Vagrantfile for a Ubuntu 12.04 LTS machine.
To bring the box up run `vagrant up` from the base directory - this will
start the box and provision it with the contents of `scripts/provision.sh`


### Running the style checker and unit tests
To test with Vagrant:
1. Bring the box up with `vagrant up`
2. Run the tests `vagrant ssh -c "/vagrant/scripts/test.sh"


## Testing on the base OS
### Running the style checker and unit tests
To run the tests you need the following:
1. Python 2.7.X 
2. Flake8
3. Nose

After installing these just run `scripts/test.sh`
