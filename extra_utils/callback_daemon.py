#!/usr/bin/env python

import time, os

def main():
    while True:
        exit_status = os.system('./all_callback.py')
        if exit_status != 0:
            print "exit_status was", exit_status, "breaking"
            break
        print 'call done'
        time.sleep(120)

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'cxze.settings'
    main()



