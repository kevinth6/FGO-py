import fgoDevice
import fgoSchedule
from fgoFuse import TimeoutException
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import FlowException, TksCommon, AbandonException
from fgoKernel import Battle, Turn, ScriptStop
from tksContext import TksContext
from fgoMetadata import servantData
from fgoConst import KEYMAP

logger = getLogger('TksBattle')

MAX_DEFEATED_TIMES = 2
MAX_DIALOGS_BEFORE_BATTLE = 5


class TksBattle(Battle):
    def __init__(self, context):
        self.common = TksCommon()
        self.context = context
        super().__init__(TksTurn)
        self.turnProc.context = context
        self.turnProc.turns = context.cur_job_context().turns()

    def check_options(self):
        logger.info('check battle options')
        TksDetect().click(P_BATTLE_OPTION)
        if not self.common.wait(IMG.TKS_BATTLE_ESCAPE, A_BATTLE_OPTIONS):
            raise FlowException("Can't open battle option menu")
        # close all options here
        changed = False
        while TksDetect().find_and_click(IMG.TKS_BATTLE_OPTION_OPEN, A_BATTLE_OPTIONS):
            logger.info('disable battle option ')
            changed = True
        self.common.click(P_BATTLE_OPTION_CLOSE, 1)
        if changed:
            # enable double speed
            logger.info('enable double speed')
            self.common.click(P_BATTLE_ATTACK, 1) \
                .wait(IMG.TKS_BATTLE_BACK, A_BATTLE_CMD) \
                .click(P_BATTLE_SPEED, 1) \
                .click(P_BATTLE_BACK, 2)
        self.context.battle_options_checked = True

    def __call__(self):
        if (not self.context.battle_options_checked) and TksDetect(0, .3).isTurnBegin():
            self.check_options()
        return super().__call__()


class TksTurn(Turn):
    def __init__(self):
        super().__init__()
        self.context = None  # has to be set after constructor
        self.turns = None  # has to be set after constructor

    def __call__(self, turn):
        jc = self.context.cur_job_context()
        if not self.turns or turn > len(self.turns) or (not jc.force_turns() and turn > TksDetect(.2).getStage()):
            super().__call__(turn)
        else:
            try:
                self._setup_turn(turn)
                logger.info(
                    f'TksTurn {turn} Stage {self.stage} StageTurn {self.stageTurn} {[i[0] for i in self.servant]}')
                turn_conf = self.turns[turn - 1]
                for skill in self._parse_skills(turn_conf):
                    if skill.startswith('m'):
                        skill = skill[1:]
                        if len(skill) == 4:
                            self.castMasterSkillWithSwap(int(skill[0]), int(skill[2]), int(skill[3]))
                        else:
                            self.castMasterSkill(int(skill[0]), (int(skill[1]) if len(skill) > 1 else 0))
                    else:
                        self.castServantSkill(int(skill[0]), int(skill[1]), (int(skill[2]) if len(skill) > 2 else 0))
                fgoDevice.device.perform(' ', (2100,))
                cards = self._parse_cards(str(turn_conf['cards']))
                logger.info(f'cards: {cards}')
                fgoDevice.device.perform(cards, (300, 300, 2300, 1300, 6000))
            except TimeoutException as tex:
                raise tex
            except Exception as ex:
                logger.error(ex, exc_info=True)
                super().__call__(turn)

    def _setup_turn(self, turn):
        TksDetect(.2)
        self.stage, self.stageTurn = [t := TksDetect.cache.getStage(), 1 + self.stageTurn * (self.stage == t)]
        if turn == 1:
            TksDetect.cache.setupServantDead()
            self.stageTotal=TksDetect.cache.getStageTotal()
            self.servant=[(lambda x:(x,)+servantData.get(x,(0,0,0,0,(0,0),((0,0),(0,0),(0,0)))))(TksDetect.cache.getFieldServant(i))for i in range(3)]
        else:
            self._setup_servant_dead()
        if self.stageTurn == 1:
            TksDetect.cache.setupEnemyGird()
        self.enemy=[TksDetect.cache.getEnemyHp(i)for i in range(6)]
        if self.stageTurn==1 or self.enemy[self.target]==0:
            self.target=numpy.argmax(self.enemy)

    def _setup_servant_dead(self):
        for i in(i for i in range(3)if TksDetect.cache.isServantDead(i)):
                self.servant[i]=(lambda x:(x,)+servantData.get(x,(0,0,0,0,(0,0),((0,0),(0,0),(0,0)))))(TksDetect.cache.getFieldServant(i))
                self.countDown[0][i]=[0,0,0]

    def _parse_skills(self, conf):
        ret = []
        if 'skills' in conf:
            for skill_str in str(conf['skills']).split(','):
                skill_str = skill_str.strip()
                if(len(skill_str) > 0) :
                    ret.append(skill_str)
        return ret
    
    def _parse_cards(self, cards):
        TksDetect(.2)
        colors = TksDetect.cache.getCardColor()  # Example: [0,1,0,2,2]
        color_map = {'a': 0, 'q': 1, 'b': 2}    # art=0, quick=1, buster=2
        used_indices = []
        result = []
        for ch in cards:
            if ch in color_map:  # card type
                target_color = color_map[ch]
                # find first matching unused card
                found = False
                for idx, card_color in enumerate(colors):
                    if card_color == target_color and idx + 1 not in used_indices:
                        result.append(str(idx + 1))
                        used_indices.append(idx + 1)
                        found = True
                        break
                # fallback: pick the first unused card from 1 to 5
                if not found:
                    for idx in range(1, 6):
                        if idx not in used_indices:
                            result.append(str(idx))
                            used_indices.append(idx)
                            break
            elif ch.isdigit():
                num = int(ch)
                if num > 5:
                    result.append(ch)  # keep as is
                else:
                    if num not in used_indices:
                        result.append(ch)
                        used_indices.append(num)
                    # ignore if already used
        return ''.join(result)

    def castMasterSkillWithSwap(self, skill, servant1, servant2):
        self.countDown[1][skill] = 15
        fgoDevice.device.perform('Q' + 'WER'[skill], (500, 500))
        fgoDevice.device.perform(('TYUIOP'[servant1 - 1], 'TYUIOP'[servant2 - 1], 'Z'), (500, 500, 2600))
        while not TksDetect().isTurnBegin():
            pass
        TksDetect(.5)
        self._setup_servant_dead()


class TksBattleGroup:
    def __init__(self, context, run_once=False):
        self.context = context
        self.run_once = run_once
        self.defeated = 0
        self.common = TksCommon()
        self.jc = self.context.cur_job_context()

    def __call__(self, check_options=True):
        logger.info('enter battle group')
        while True:
            if not self._before_battle():
                logger.info("can't enter battle, exit battle group")
                return False
            battle = TksBattle(self.context)
            if not self._after_battle(battle(), battle.result):
                logger.info('Exit battle group ')
                break
        return True

    def choose_team(self):
        if (team_index := self.jc.team_index()) is not None:
            pass
        else:
            team_index = 0
        logger.info('choose team ' + str(team_index))
        if TksDetect.cache.getTeamIndex() != team_index:
            fgoDevice.device.perform('\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79'[team_index], (1000,))
        if self.jc.use_pot() and TksDetect.cache.appear(IMG.TKS_POT_CLOSE, A_POT_BUTTONS):
            self.common.click(P_POT_BTN, .8)
        elif not self.jc.use_pot() and TksDetect.cache.appear(IMG.TKS_POT_OPEN, A_POT_BUTTONS):
            self.common.click(P_POT_BTN, .8)

    def battle_completed(self):
        while True:
            t = TksDetect().cache
            if t.isBattleContinue():
                break
            elif self.common.handle_special_drop(t, self.context):
                logger.info('Special dropped.')
            elif t.isAddFriend():
                logger.info('add friend')
                fgoDevice.device.perform('X', (300,))
            elif p := self.common.find_dialog_close(t):
                t.click(p, after_delay=.8)
            elif t.isMainInterface() or t.is_on_map() or t.is_on_menu():
                break
            elif self.common.skip_possible_story():
                pass
            else:
                fgoDevice.device.perform(' ', (600,))

    def _before_battle(self):
        dialogs = 0
        while True:
            t = TksDetect(.8, .8).cache
            if t.isTurnBegin():
                logger.info('turn begin')
                break
            elif t.isApEmpty():
                logger.info('AP empty.')
                if not self.common.eat_apple(self.context):
                    return False
            elif p := t.find(IMG.TKS_DIALOG_CLOSE2, A_DIALOG_BUTTONS):
                # could be friend constraint confirm
                logger.info('Dialog pops up. click close')
                t.click(p)
                dialogs += 1
                if dialogs >= MAX_DIALOGS_BEFORE_BATTLE:
                    raise AbandonException('Too many dialogs here, may meet some constraint rules.')
            elif t.appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT):
                logger.info('choose friend. ')
                self.choose_friend()
                # could enter the battle directly if it's in battle continue
            elif t.appear(IMG.TKS_TEAM_CONFIRM, A_TOP_RIGHT):
                self.choose_team()
                fgoDevice.device.perform(' ', (2000,))
            elif t.appear(IMG.TKS_CANCEL_TEAM, A_TOP_MIDDLE):
                logger.info("Cancel team dialog found")
                t.find_and_click(IMG.TKS_DIALOG_DECIDE, A_DIALOG_BUTTONS, after_delay=.8)
            elif t.appear_btn(B_SUMMON_SALE):
                # synthesis only handled in cleanup
                raise FlowException('Card position full. Need synthesis. ')
            else:
                self.common.skip_possible_story()
            fgoDevice.device.press('\xBB')
        return True

    def _after_battle(self, completed, result):
        if completed:
            logger.info('battle completed. result ' + str(result))
            if result:
                self.jc.battle_completed += 1
                self.jc.total_turns += result['turn']
                self.jc.total_time += result['time']
                self.jc.materials = TksContext.dict_add(self.jc.materials, result['material'])

            fgoDevice.device.perform(' ', (600,))
            self.battle_completed()
            self.defeated = 0
        else:
            logger.info('battle failed. result ' + str(result))
            self.jc.battle_failed += 1
            self.defeated += 1
            fgoDevice.device.perform('CI', (1000, 1000,))
            self.common.click(P_FAIL_CLOSE, 1)
            if self.defeated > MAX_DEFEATED_TIMES:
                raise AbandonException('Defeated too many times')

        # handle battle continue
        if TksDetect().isBattleContinue():
            if self.run_once:
                logger.info('Run once, cancel battle continue')
                fgoDevice.device.perform('F', (1000,))
                return False
            else:
                logger.info('battle continue')
                fgoDevice.device.perform('L', (1000,))
                return True
        else:
            return False

    def choose_friend(self):
        if not self.jc.friend_reisou():
            if not self.jc.campaign_friend_checked and \
                    (self.jc.campaign_servant() or self.jc.campaign_reisou()):
                self._handle_campaign_friend_options()
                self.jc.campaign_friend_checked = True
        if self.jc.friend_class() and self.jc.friend_class() in PS_FRIEND_CLASSES:
            schedule.sleep(1.5)
            self.common.click(PS_FRIEND_CLASSES[self.jc.friend_class()], after_delay=1.5)

        has_friend = True
        count = 0
        while True:
            t = TksDetect(.2, .5)
            if t.isNoFriend() or not has_friend:
                self.common.wait(IMG.TKS_FRIEND_REFRESH, A_FRIEND_OPTIONS_BAR)
                logger.info('Refresh friends.')
                if self.jc.friend_class() and self.jc.friend_class() in PS_FRIEND_CLASSES:
                    self.common.click(PS_FRIEND_CLASSES[self.jc.friend_class()], after_delay=1)
                fgoDevice.device.perform('\xBAK', (800, 1000))
                has_friend = True
                count += 1
                if count > 50:
                    raise ScriptStop('Can refresh friends, stuck and exit.')
                schedule.sleep(2)
            else:
                if p := self.common.scroll_and_find(self._friend_find_func(), end_pos=P_FRIEND_SCROLL_END,
                                                    top_pos=P_FRIEND_SCROLL_TOP):
                    return self.common.click(p)
                else:
                    has_friend = False

    def _friend_find_func(self):
        fr = self.jc.friend_reisou() and self.jc.friend_reisou() in FRIEND_REISOUS
        fs = self.jc.friend_servant() and self.jc.friend_servant() in FRIEND_SERVANTS
        if fr and fs:
            return self._find_by_reisou_and_name
        elif fr:
            return lambda t, i: t.find(FRIEND_REISOUS[self.jc.friend_reisou()], A_FRIEND_ICONS)
        elif fs:
            return lambda t, i: t.find(FRIEND_SERVANTS[self.jc.friend_servant()], A_FRIEND_NAMES)
        else:
            return lambda t, i: KEYMAP['8']

    def _find_by_reisou_and_name(self, t, i):
        ps = t.find_multiple(FRIEND_REISOUS[self.jc.friend_reisou()], A_FRIEND_ICONS)
        for p in ps:
            rect = t.surround((p[0] + 412, p[1] - 50), 450, 50)
            if t.find(FRIEND_SERVANTS[self.jc.friend_servant()], rect):
                return p

    def _handle_campaign_friend_options(self):
        logger.info('Handle campaign friend options')
        t = TksDetect(.3, .3).cache
        if p := (t.find(IMG.TKS_FRIEND_OPTIONS, A_FRIEND_OPTIONS_BAR)
                 or t.find(IMG.TKS_FRIEND_OPTIONS_ON, A_FRIEND_OPTIONS_BAR)):
            schedule.sleep(2)
            self.common.click_and_wait(p, IMG.TKS_DIALOG_DECIDE, A_DIALOG_BUTTONS)
        else:
            return

        logger.info('In campaign friend options dialog')
        self.common.click(P_FRIEND_OPTION_SCROLL_TOP, after_delay=.5)
        self.common.click(P_FRIEND_OPTION_RESET, after_delay=.5)
        if self.jc.campaign_servant():
            self.common.click(P_FRIEND_CAMPAIGN_SERVANT, after_delay=.5)
        if self.jc.campaign_reisou():
            self.common.click(P_FRIEND_CAMPAIGN_REISOU, after_delay=.5)
            if self.jc.campaign_reisou() == 2:
                self.common.click(P_FRIEND_OPTION_SCROLL_MID)
                TksDetect(.3, .3).find_and_click(IMG.TKS_FRIEND_REISOU_MAX, after_delay=.5)

        if (idx := self.jc.campaign_reisou_idx()) is not None:
            logger.info(f'Setup campaign reisou by idx {idx}')
            func = lambda t: self._disable_all_reisou(t)
            self._friend_option_scroll(func)
            reisou_imgs = []
            func = lambda t: self._scan_reisou(t, reisou_imgs)
            self._friend_option_scroll(func)
            logger.info(f'Found campaign imgs: {len(reisou_imgs)}')
            if idx >= len(reisou_imgs):
                raise ScriptStop(f'Unable to find the campaign reisou.')
            func = lambda t: self._enable_reisou(t, reisou_imgs[idx])
            self._friend_option_scroll(func, True)

        TksDetect.cache.find_and_click(IMG.TKS_DIALOG_DECIDE, after_delay=.7)

    def _friend_option_scroll(self, func, find_return=False):
        self.common.click(P_FRIEND_OPTION_SCROLL_TOP, after_delay=.5)
        for i in range(10):
            ret = func(TksDetect())
            if find_return and ret:
                return ret
            if TksDetect.cache.is_list_end(P_FRIEND_OPTION_SCROLL_END):
                break
            self.common.swipe(A_SWIPE_FRIEND_OPTION_DOWN)
            schedule.sleep(.5)

    def _disable_all_reisou(self, t):
        ps = t.find_multiple(IMG.TKS_FRIEND_OPTION_SHOW, A_FRIEND_SHOW_BUTTONS, .06)
        for p in ps:
            t.click(p, after_delay=.5)

    def _scan_reisou(self, t, reisou_imgs):
        ps = t.find_multiple(IMG.TKS_FRIEND_OPTION_HIDE, A_FRIEND_SHOW_BUTTONS, .06)
        for p in ps:
            rect = t.surround((p[0] - 500, p[1] - 20), 88, 50)
            exist = False
            for img in reisou_imgs:
                if t.appear(img, t.expand(rect, 5), threshold=.05):
                    exist = True
                    break
            if not exist:
                reisou_imgs.append([t._crop(rect), None])

    def _enable_reisou(self, t, img):
        if p := t.find(img):
            t.click((p[0] + 500, p[1]), after_delay=.5)
            return True
        return False
