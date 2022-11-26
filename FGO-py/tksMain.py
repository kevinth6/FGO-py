import argparse, cv2
import random

from fgoLogging import getLogger
from tksDetect import *
import fgoDevice, fgoSchedule
from fgoDetect import Detect, IMG
from tksCommon import TksCommon, FlowException, AbandonException
from tksInterface import TksInterface
from tksContext import TksContext, TksJobContext
from tksBattle import TksBattleGroup, TksTurn
from fgoFuse import StuckException
from tksCampaign import TksCampaign
from tksExpBall import TksExpBall

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
            if t.isTurnBegin():
                logger.info('In battle, complete battle first')
                TksBattleGroup(TksContext.anonymous_context(), run_once=True)()
            elif p := t.find(IMG.TKS_APP_ICON):
                logger.info('Game closed, reopen')
                t.click(p)
            elif t.appear(IMG.TKS_CONTRACT, A_CONTRACT_TITLE, threshold=.02):
                logger.info('Click contract agree')
                t.click(P_CONTRACT_AGREE)
            elif t.find_and_click(IMG.TKS_LOGIN, A_LOGIN_BOX, threshold=.02):
                logger.info('Click login')
            elif t.find_and_click(IMG.TKS_NOT_CONTINUE, A_DIALOG_BUTTONS):
                logger.info('Click not continue')
            elif t.find_and_click(IMG.TKS_INTERRUPTED_BATTLE_ENTER, A_DIALOG_BUTTONS):
                logger.info('Continue interrupted battle')
            elif t.isMainInterface() or t.is_on_top() or t.is_on_map():
                self.common.close_all_dialogs()
                break
            elif p := self.common.find_dialog_close(t):
                t.click(p, after_delay=1)
            elif self.common.skip_possible_story():
                pass
            else:
                self.common.click(P_TL_BUTTON, after_delay=.2)
                fgoDevice.device.perform('\xBB', (200,))
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

        assert fgoDevice.device.available
        context = TksContext(self.config, 'extertena')
        context.current_job = 'campaign_free'
        # TksBattleGroup(context).choose_friend()
        # self._cleanup()
        # TksCommon().back_to_top()
        # TksExpBall(context).burning()
        # turn = TksTurn()
        # turn._setup_turn(1)
        # turn.castServantSkill(0, 1, 3)
        # fgoDevice.device.perform('Q' + 'WER'[2], (300, 300))
        # fgoDevice.device.perform(('TYUIOP'[2], 'TYUIOP'[4], 'Z'), (300, 300, 2600))
        # turn._setup_turn(2)
        # turn.castMasterSkill(0, 7)
        # fgoDevice.device.perform(' ', (2100,))
        # fgoDevice.device.perform('612345', (300, 300, 2300, 1300, 6000))

        # TksExpBall(context).synthesis_servant()
        # context.save()
        # TksCommon().back_to_top()
        # TksCampaign(context)()
        # TksInterface(context).retrieve_week_awards()

        # TksBattleGroup(context).choose_friend()
        # TksCommon().handle_special_drop(TksDetect())
        # print(TksDetect().isAddFriend())
        # for i in range(10):
        #     print(TksDetect().find(FRIEND_REISOUS['exp'], A_FRIEND_ICONS))

        # self.do_run()

    def do_run(self):
        """main run entry"""
        self._cleanup()
        for account in self.config['accounts']:
            logger.info("run for account " + account)
            context = TksContext(self.config, account)
            times = 0
            while times < 3:
                try:
                    itfc = TksInterface(context)
                    itfc.switch_to_account(context.account)
                    TksCommon().back_to_top()
                    itfc.retrieve_week_awards()
                    break
                except Exception as ex:
                    logger.error(ex, exc_info=True, stack_info=True)
                    logger.info('Cleanup and continue')
                    self._cleanup()
                    times += 1
            if times >= 3:
                logger.error('Exception times exceed 3. Exit')
                continue

            for job_name in context.job_names:
                context.current_job = job_name
                times = 0
                while times < 3:
                    try:
                        logger.info("Run job " + job_name)
                        getattr(self, f'run_{context.job_configs[job_name]["type"]}')(context)
                        logger.info("Finish running job " + job_name)
                        break
                    except (StuckException, FlowException) as ex:
                        logger.error(ex, exc_info=True, stack_info=True)
                        logger.info('Cleanup and continue')
                        self._cleanup()
                        times += 1
                    except AbandonException as ex:
                        logger.error(ex, exc_info=True, stack_info=True)
                        logger.error('Abandon this job, continue next')
                        self._cleanup()
                        break
                if times >= 3:
                    logger.error('Exception times exceed 3. Abandon this job, continue next')

            context.save()
            logger.info("Finish running account " + account)

    def run_free(self, context):
        cjc = context.cur_job_context()
        self.common.back_to_top()
        TksInterface(context).go_free_instance(cjc.chapter(), cjc.section(), cjc.instance())
        return TksBattleGroup(context)()

    def run_campaign_main(self, context):
        self.common.back_to_top()
        return TksCampaign(context).run_main_tasks()

    def run_campaign_free(self, context):
        self.common.back_to_top()
        return TksCampaign(context).run_free()

    def run_exp_ball(self, context):
        self.common.back_to_top()
        TksExpBall(context)()

    parser_tks = argparse.ArgumentParser(prog='tks', description='Tulkas Extensions for FGO-py')
    parser_tks_ = parser_tks.add_subparsers(title='tkssubcmd', required=True, dest='subcmd')
    parser_tks_find = parser_tks_.add_parser('find', help=do_find.__doc__)
    parser_tks_find.add_argument('name', help='IMG name, could be lower case')
    parser_tks_find.add_argument('-t', '--threshold', help='threshold to find the IMG')
    parser_tks_test = parser_tks_.add_parser('test', help=do_test.__doc__)
    parser_tks_run = parser_tks_.add_parser('run', help=do_run.__doc__)

    complete_table = {
        '': ['find', 'test', 'run']
    }
