#! /usr/bin/env python2.7
""" The IRCD Daemon"""


if __name__ == "__main__":
    from argparse import ArgumentParser

    flag_parser = ArgumentParser(description="IRCDD options", conflict_handler='resolve')

# Place any extra arguments we need here in the format below. Specify type if we want
#  to only accept certain types of input. Be warned that this will cause an error that
#  exits the program. 
# To make it an optional flag proceed the name with a '-' or '--'
    flag_parser.add_argument("-hn", "--hostname", help="The Hostname for the server")
    flag_parser.add_argument("-p", "--portnumber", help="The Portnumber for the server",
                         type=int)
 
    valid_args, unknown = flag_parser.parse_known_args()
    input_flags = vars(valid_args)
    flags = {x: input_flags[x] for x in input_flags if input_flags[x] is not None}

    if unknown:
        print "The following flags are invalid and have been ignored by IRCDD:  ", ', '.join(map(str, unknown))

