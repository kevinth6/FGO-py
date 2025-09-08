import argparse, cv2, time
import random

from fgoLogging import getLogger
from tksDetect import *
import fgoDevice, fgoSchedule
from fgoDetect import Detect, IMG
from tksCommon import TksCommon, FlowException, AbandonException
from tksInterface import TksInterface
from tksContext import TksContext, load_stat
from tksBattle import TksBattleGroup, TksBattle, TksTurn
from fgoFuse import fuse, StuckException, TimeoutException
from tksExpBall import TksExpBall
from fgoSchedule import ScriptStop

logger = getLogger('TksMain')


class TksMain:

    def __init__(self, args, config):
        self.args = TksMain.parser_tks.parse_args(args)
        self.config = config
        self.common = TksCommon()

    def __call__(self):
        fgoDevice.Device.enumDevices()
        getattr(self, f'do_{self.args.subcmd}')()

    def _cleanup(self):
        assert fgoDevice.device.available
        fuse.timeout_time = time.time() + 900
        while True:
            try:
                t = TksDetect().cache
                if t.isTurnBegin():
                    logger.info('In battle, complete battle first')
                    TksBattleGroup(TksContext.anonymous_context(), run_once=True)()
                elif t.appear(IMG.TKS_CONTRACT, A_CONTRACT_TITLE, threshold=.02):
                    logger.info('Click contract agree')
                    t.click(P_CONTRACT_AGREE)
                elif t.find_and_click(IMG.TKS_LOGIN, A_LOGIN_BOX, threshold=.02):
                    logger.info('Click login')
                elif t.find_and_click(IMG.TKS_REFRESH, A_LOGIN_BOX, threshold=.02):
                    logger.info('Click refresh')
                elif t.find_and_click(IMG.TKS_NOT_CONTINUE, A_DIALOG_BUTTONS):
                    logger.info('Click not continue')
                elif t.find_and_click(IMG.TKS_INTERRUPTED_BATTLE_ENTER, A_DIALOG_BUTTONS):
                    logger.info('Continue interrupted battle')
                elif t.find_and_click(IMG.TKS_DIALOG_UPDATE, A_DIALOG_BUTTONS):
                    logger.info('Click update game')
                elif t.appear_btn(B_SUMMON_SALE):
                    logger.info('Card position full. Start synthesis. ')
                    self.run_synthesis(TksContext.anonymous_context())
                elif t.isMainInterface() or t.is_on_top() or t.is_on_map():
                    self.common.close_all_dialogs()
                    break
                elif p := self.common.find_dialog_close(t):
                    t.click(p, after_delay=1)
                elif p := t.find(IMG.TKS_APP_ICON):
                    logger.info('Game closed, reopen')
                    t.click(p)
                elif self.common.skip_possible_story():
                    pass
                else:
                    self.common.click(P_TL_BUTTON, after_delay=.2)
                    fgoDevice.device.perform('\xBB', (200,))
            # except TimeoutException as ex:
            #     self._exit_exception(ex)
            # except ScriptStop as ex:
            #     self._exit_exception(ex)
            except Exception as ex:
                self._exit_exception(ex)
            schedule.sleep(.3)

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
        context = TksContext(self.config, 'tulkasmstr')
        context.current_job = 'run_campaign'
        self.run_free(context)
        # TksBattleGroup(context)._handle_campaign_friend_options()

        # self.run_exp_ball(context)
        # g = TksBattleGroup(context, run_once=True)
        # g.jc.campaign_friend_checked = True
        # g.choose_friend()
        # g.choose_friend()

        # battle = TksBattle(context)
        # battle()
        
        # context.current_job = 'any_rank_up'
        # TksCommon().back_to_top()
        # TksCampaign(context).run_free()
        # context.save_stat()
        
        # cjc = context.cur_job_context()
        # for i in range(10):
        #     TksCommon().back_to_top()
        #     TksInterface(context).go_free_instance(cjc.chapter(), cjc.section(), 'qp4')
        # self.run_synthesis(context)
        # print(context.current_job[20])
        # self.run_free(context)
        # turn._setup_turn(1)

        # TksBattleGroup(context).choose_friend()
        # self._cleanup()
        # TksCommon().back_to_top()
        # turn = TksTurn()
        # print(turn._parse_cards('b6b12345'))
        # print(turn._parse_cards('67812345'))
        # print(turn._parse_cards('q7a12345'))
        # turn._setup_turn(1)
        # turn.castServantSkill(1, 1, 1)
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

        # cv2.imwrite(name:='tmpimg',xxx,[cv2.IMWRITE_PNG_COMPRESSION,9])
        # self.do_run()

    def do_run(self):
        """main run entry"""
        self._cleanup()
        (last_account, last_apple) = load_stat(self.config)
        check_last = True
        for account in self.config['accounts']:
            if check_last and last_account and account != last_account:
                logger.info(f"last account {last_account}, skip this account {account}")
                continue
            check_last = False
            logger.info("run for account " + account)
            context = TksContext(self.config, account)
            if last_apple and account == last_account:
                context.apple_used = last_apple
            context.save_stat()
            times = 0
            while times < 3:
                try:
                    fuse.timeout_time = time.time() + 300
                    itfc = TksInterface(context)
                    itfc.switch_to_account(context.account)
                    TksCommon().back_to_top()
                    itfc.retrieve_week_awards()
                    break
                except Exception as ex:
                    self._report_exception(ex)
                    logger.info('Cleanup and continue')
                    self._cleanup()
                    times += 1
            if times >= 3:
                logger.error('Exception times exceed 3. Exit')
                continue

            for job_name in context.job_names:
                context.current_job = job_name
                jc = context.cur_job_context()
                if not jc.type():
                    continue
                times = 0
                while times < 3:
                    try:
                        logger.info("Run job " + job_name)
                        if jc.timeout():
                            fuse.timeout_time = time.time() + jc.timeout()
                        else:
                            fuse.timeout_time = None
                        getattr(self, f'run_{jc.type()}')(context)
                        logger.info("Finish running job " + job_name)
                        break
                    except (StuckException, FlowException) as ex:
                        self._report_exception(ex)
                        logger.info('Cleanup and continue')
                        self._cleanup()
                        times += 1
                    except (AbandonException, TimeoutException) as ex:
                        self._report_exception(ex)
                        logger.error('Abandon this job, continue next')
                        self._cleanup()
                        break
                    except ScriptStop as ex:
                        self._exit_exception(ex)
                if times >= 3:
                    logger.error('Exception times exceed 3. Abandon this job, continue next')

            context.save()
            context.remove_stat()
            logger.info("Finish running account " + account)

    def _report_exception(self, ex):
        logger.error(ex, exc_info=True, stack_info=True)
        if TksDetect.cache:
            TksDetect.cache.save('fgoLog/Exception')

    def _exit_exception(self, ex):
        if TksDetect.cache:
            TksDetect.cache.save('fgoLog/Exception')
        fuse.save()
        raise ex

    def run_free(self, context):
        self.common.back_to_top()
        return TksInterface(context).run_free()

    def run_reishift(self, context):
        self.common.back_to_top()
        return TksInterface(context).run_reishift()

    def run_exp_ball(self, context):
        self.common.back_to_top()
        TksExpBall(context)()

    def run_synthesis(self, context):
        exp_ball = TksExpBall(context)
        # if not context.cur_job_context().disable_burning():
        #     exp_ball.burning()
        exp_ball.synthesis()

    def run_interlude(self, context):
        self.common.back_to_top()
        TksInterface(context).run_interlude()

    def run_rank_up(self, context):
        self.common.back_to_top()
        TksInterface(context).run_rank_up()

    def run_skip(self, context):
        logger.info('skip this job')

    parser_tks = argparse.ArgumentParser(prog='tks', description='Tulkas Extensions for FGO-py')
    parser_tks_ = parser_tks.add_subparsers(title='tkssubcmd', required=True, dest='subcmd')
    parser_tks_find = parser_tks_.add_parser('find', help=do_find.__doc__)
    parser_tks_find.add_argument('name', help='IMG name, could be lower case')
    parser_tks_find.add_argument('-t', '--threshold', help='threshold to find the IMG')
    parser_tks_test = parser_tks_.add_parser('test', help=do_test.__doc__)
    parser_tks_run = parser_tks_.add_parser('run', help=do_run.__doc__)

    complete_table = {'': ['find', 'test', 'run']}
