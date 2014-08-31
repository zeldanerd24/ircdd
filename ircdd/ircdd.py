#! /usr/bin/env python2.7
""" The IRCD Daemon"""


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="IRCDD options")

    parser.add_argument("-v", "--verbose", action="store_true",
                        default=False, help="log extra information")

    args = parser.parse_args()
