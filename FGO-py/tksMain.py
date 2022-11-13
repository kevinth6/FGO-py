import argparse, cv2
from fgoLogging import getLogger
from tksDetect import TksDetect, INTERFACES
import fgoDevice
from fgoDetect import Detect, IMG
from tksCommon import TksCommon

logger = getLogger('TksMain')


class TksMain:

    def __init__(self, args, config):
        self.args = TksMain.parser_tks.parse_args(args)
        self.config = config

    def __call__(self):
        assert fgoDevice.device.available
        getattr(self, f'do_{self.args.subcmd}')()

    def do_find(self):
        """find IMG from screen and print the location to console"""
        print(TksDetect().cache.find(getattr(IMG, self.args.name.upper())))

    def do_test(self):
        """for test"""
        TksCommon(self.config).back_to_menu()

    parser_tks = argparse.ArgumentParser(prog='tks', description='Tulkas Extensions for FGO-py')
    parser_tks_ = parser_tks.add_subparsers(title='tkssubcmd', required=True, dest='subcmd')
    parser_tks_find = parser_tks_.add_parser('find', help=do_find.__doc__)
    parser_tks_find.add_argument('name', help='IMG name, could be lower case')
    parser_tks_find.add_argument('-t', '--threshold', help='threshold to find the IMG')
    parser_tks_test = parser_tks_.add_parser('test', help=do_test.__doc__)

    complete_table = {
        '': ['find']
    }
