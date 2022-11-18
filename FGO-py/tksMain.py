import argparse, cv2
import random

from fgoLogging import getLogger
from tksDetect import *
import fgoDevice, fgoSchedule
from fgoDetect import Detect, IMG
from tksCommon import TksCommon, save_get, FlowException
from tksInterface import TksInterface
from tksContext import TksContext, TksJobContext
from tksBattle import TksBattle, TksBattleGroup
from fgoFuse import StuckException
from tksCampaign import TksCampaign

logger = getLogger('TksMain')


class TksMain:

    def __init__(self, args, config):
        self.args = TksMain.parser_tks.parse_args(args)
        self.config = config
        self.common = TksCommon()

    def __call__(self):
        getattr(self, f'do_{self.args.subcmd}')()

    def _cleanup(self):
        assert fgoDevice.device.available
        while True:
            t = TksDetect().cache
            if t.isMainInterface():
                self.common.close_all_dialogs()
                break
            elif t.isTurnBegin():
                logger.info('In battle, complete battle first')
                TksBattleGroup(TksContext.anonymous_context(), run_once=True)()
            elif p := t.find(IMG.TKS_APP_ICON):
                logger.info('Game closed, reopen')
                t.click(p)
            elif t.appear(IMG.TKS_CONTRACT, A_CONTRACT_TITLE):
                logger.info('Click contract agree')
                t.click(P_CONTRACT_AGREE)
            else:
                fgoDevice.device.perform('\xBB\x08', (200, 500))
            schedule.sleep(.5)

    def do_find(self):
        """find IMG from screen and print the location to console"""
        print(TksDetect().cache.find(getattr(IMG, self.args.name.upper())))

    def do_test(self):
        """for test"""
        # TksInterface(TksCommon(self.config)).go_free_instance('campaign_20221103', '90', None)
        # context = TksContext(self.config, 'militaoccasi')
        # context.current_job = 'free1'
        # TksInterface(context).switch_to_account(context.account)
        # TksInterface(context).go_free_instance('campaign_20221103', '90', None)
        # TksBattleGroup(context)()
        # TksCommon(self.config).scroll_and_click(IMG.TKS_FREE_DONE, A_INSTANCE_MENUS)
        self._cleanup()
        context = TksContext(self.config, 'militaoccasi')
        context.current_job = 'campaign_cur'
        TksCommon().back_to_top()
        TksCampaign(context)()

        #self.do_run()

    def do_run(self):
        """main run entry"""
        self._cleanup()
        for account in self.config['accounts']:
            logger.info("run for account " + account)
            context = TksContext(self.config, account)
            TksInterface(context).switch_to_account(context.account)
            for job_name in context.job_names:
                logger.info("run job " + job_name)
                context.current_job = job_name
                try:
                    getattr(self, f'run_{context.job_configs[job_name]["type"]}')(context)
                except (StuckException, FlowException) as ex:
                    logger.error('Exception caught, ' + str(ex))
                    logger.info('Cleanup and continue next job')
                    self._cleanup()

    def run_free(self, context):
        cjc = context.cur_job_config()
        TksCommon().back_to_top()
        TksInterface(context).go_free_instance(save_get(cjc, 'chapter'), save_get(cjc, 'section'),
                                               save_get(cjc, 'instance'))
        TksBattleGroup(context)()

    parser_tks = argparse.ArgumentParser(prog='tks', description='Tulkas Extensions for FGO-py')
    parser_tks_ = parser_tks.add_subparsers(title='tkssubcmd', required=True, dest='subcmd')
    parser_tks_find = parser_tks_.add_parser('find', help=do_find.__doc__)
    parser_tks_find.add_argument('name', help='IMG name, could be lower case')
    parser_tks_find.add_argument('-t', '--threshold', help='threshold to find the IMG')
    parser_tks_test = parser_tks_.add_parser('test', help=do_test.__doc__)
    parser_tks_run = parser_tks_.add_parser('run', help=do_run.__doc__)

    complete_table = {
        '': ['find']
    }
