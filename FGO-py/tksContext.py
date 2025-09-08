import copy, time, yaml, os, collections, json
from tksCommon import FlowException


def safe_get(dict, name):
    return dict[name] if name in dict else None

def load_stat(config):
    if os.path.exists(config['stat_file']):
        with open(config['stat_file'], "r", encoding="utf-8") as f:
            stat = json.load(f)
            return (stat['account'], stat['apple_used'])
    return (None, None)

class TksContext:

    def __init__(self, config, account):
        self.config = config
        self.account = account
        self.start_time = time.time()
        self._setup_presets(config, account)
        self._setup_jobs_config(config, account)
        self._setup_job_contexts()
        self.current_job = None
        self.battle_options_checked = False
        self.apple_used = 0

    def _setup_presets(self, config, account):
        self.presets = {}
        if ('presets' in config) and config['presets']:
            for preset_key in config['presets']:
                self.presets[preset_key] = copy.deepcopy(config['presets'][preset_key])

        account_presets = (config['account_presets'][account]) if \
            ('account_presets' in config) \
            and config['account_presets'] \
            and (account in config['account_presets']) else None

        if account_presets:
            for preset_key in account_presets:
                self.job_configs[preset_key].update(account_presets[preset_key])

    def _setup_jobs_config(self, config, account):
        self.job_configs = {}
        self.job_names = []
        if 'all_jobs' in config:
            for job in config['all_jobs']:
                self.job_configs[job['name']] = copy.deepcopy(job)
                self.job_names.append(job['name'])

        account_jobs = (config['account_jobs'][account]) if \
            ('account_jobs' in config) \
            and config['account_jobs'] \
            and (account in config['account_jobs']) else None
        if account_jobs:
            for job in account_jobs:
                if job['name'] in self.job_configs:
                    self.job_configs[job['name']].update(copy.deepcopy(job))
                else:
                    self.job_configs[job['name']] = copy.deepcopy(job)

        # setup preset
        for job_name in self.job_configs:
            job = self.job_configs[job_name]
            if 'use_preset' in job and job['use_preset'] and job['use_preset'] in self.presets:
                job.update(self.presets[job['use_preset']])

    def _setup_job_contexts(self):
        self.job_contexts = {}
        for job in self.job_configs:
            self.job_contexts[job] = TksJobContext(self.job_configs[job])

    def cur_job_config(self):
        if self.current_job and self.current_job in self.job_configs:
            return self.job_configs[self.current_job]
        else:
            raise FlowException("Can't get current job config, account: " + self.account + ", job: " + self.current_job)

    def cur_job_context(self):
        if self.current_job and self.current_job in self.job_contexts:
            return self.job_contexts[self.current_job]
        else:
            raise FlowException("Can't get current job context, account: " + self.account + ", job: " +
                                self.current_job)

    def apple_kind(self):
        return safe_get(self.config, 'apple_kind')

    def apples(self):
        return safe_get(self.config['account_apples'], self.account)

    def apple_remaining(self):
        return self.apples() and self.apple_used < self.apples()

    def save(self, path='tksResult'):
        save_path = f"{path}/{self.account}"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        t = time.time()
        name = time.strftime(f'{save_path}{f"/res_%Y-%m-%d_%H.%M.%S.{round(t * 1000) % 1000:03}"}.json')
        with open(name, "w") as f:
            json.dump(self.out(), f, indent=4)

    def save_stat(self):
        with open(self.config['stat_file'], "w") as f:
            json.dump(self.out_stat(), f, indent=4)

    def out(self):
        total_comp = TksContext.sum_in_obj_dict(self.job_contexts, 'battle_completed')
        total_fail = TksContext.sum_in_obj_dict(self.job_contexts, 'battle_failed')

        ret = collections.OrderedDict()
        ret["start_time"] = time.strftime(f'%Y-%m-%d_%H.%M.%S.{round(self.start_time * 1000) % 1000:03}')
        ret['end_time'] = time.strftime(f'%Y-%m-%d_%H.%M.%S.{round(self.start_time * 1000) % 1000:03}')
        ret['battle_completed'] = total_comp
        ret['battle_failed'] = total_fail
        ret['apple_used'] = self.apple_used
        ret['jobs'] = collections.OrderedDict()
        for jck in self.job_contexts:
            ret['jobs'][jck] = self.job_contexts[jck].out()

        return ret

    def out_stat(self):
        ret = collections.OrderedDict()
        ret['account'] = self.account
        ret['apple_used'] = self.apple_used
        return ret
    
    def remove_stat(self):
        os.remove(self.config['stat_file'])

    @staticmethod
    def anonymous_context():
        config = {'accounts': ['anonymous'], 'all_jobs': [{'name': 'random-job'}]}
        ret = TksContext(config, 'anonymous')
        ret.current_job = 'random-job'
        return ret

    @staticmethod
    def avg(total, count):
        return (total / count) if count > 0 else 0

    @staticmethod
    def sum_in_obj_dict(obj_dict, key):
        ret = 0
        for dk in obj_dict:
            ret += getattr(obj_dict[dk], key)
        return ret

    @staticmethod
    def dict_add(merged, added):
        return {i: merged.get(i, 0) + added.get(i, 0) for i in merged | added}


class TksJobContext:

    def __init__(self, job_config):
        self.job_config = job_config
        self.battle_completed = 0
        self.battle_failed = 0
        self.total_turns = 0
        self.total_time = 0
        self.summon_count = 0
        self.special_drops = 0
        self.materials = {}
        self.campaign_friend_checked = False
        self.summon_option_checked = False
        self.synthesis_reisou_checked = False
        self.synthesis_reisou_food_checked = False
        self.synthesis_servant_checked = False
        self.synthesis_servant_food_checked = False
        self.servant_burning_checked = False
        self.reisou_burning_checked = False
        self.code_burning_checked = False

    def out(self):
        ret = collections.OrderedDict()
        ret["config"] = self.job_config
        ret["battle_completed"] = self.battle_completed
        ret["battle_failed"] = self.battle_failed
        ret["total_turns"] = self.total_turns
        ret["total_time"] = self.total_time
        ret["avg_turns"] = TksContext.avg(self.total_turns, self.battle_completed + self.battle_failed)
        ret["avg_time"] = TksContext.avg(self.total_time, self.battle_completed + self.battle_failed)
        ret["summon_count"] = self.summon_count
        ret["special_drops"] = self.special_drops
        ret["materials"] = self.materials
        return ret

    def type(self):
        return safe_get(self.job_config, 'type')

    def timeout(self):
        """timeout setting"""
        return safe_get(self.job_config, 'timeout')

    def team_index(self):
        """specify the team index in any battle, the highest priority"""
        return safe_get(self.job_config, 'team_index')

    def chapter(self):
        """the chapter in free running"""
        return safe_get(self.job_config, 'chapter')

    def section(self):
        """the section in free running"""
        return safe_get(self.job_config, 'section')

    def instance(self):
        """the instance in free running"""
        return safe_get(self.job_config, 'instance')

    def level(self):
        """specify the level of free instances in campaign, 1 bronze, 2 silver, 3 gold, 4 green"""
        return safe_get(self.job_config, 'level')

    def cls(self):
        """specify the cls of free instances in campaign, could be saber, lancer, etc."""
        return safe_get(self.job_config, 'cls')

    def campaign_servant(self):
        """should select the campaign servant in the friend selection options"""
        return safe_get(self.job_config, 'campaign_servant')

    def campaign_reisou(self):
        """should select the campaign reisou in the friend selection options"""
        return safe_get(self.job_config, 'campaign_reisou')

    def campaign_reisou_idx(self):
        """specify which campaign reisou to enable in the friend selection options, will disable all other,
        the index starts from 0, from top to bottom"""
        return safe_get(self.job_config, 'campaign_reisou_idx')

    def campaign_no_map(self):
        """specify if the campaign doesn't have a map, affects the instance search"""
        return safe_get(self.job_config, 'campaign_no_map')

    def friend_reisou(self):
        """specify the reisou in the friend selection, name of images in friend_reisou,
        will disable campaign_reisou & campaign_reisou_idx if set"""
        return safe_get(self.job_config, 'friend_reisou')

    def friend_class(self):
        """specify the class in the friend selection, could be saber, lancer, etc."""
        return safe_get(self.job_config, 'friend_class')

    def friend_servant(self):
        """specify the servant in the friend selection, name of images in friend_servant."""
        return safe_get(self.job_config, 'friend_servant')

    def max_summon(self):
        """max summon count in exp_ball"""
        return safe_get(self.job_config, 'max_summon')

    def max_synthesis(self):
        """max synthesis count in exp_ball, if not set, 20 by default"""
        return safe_get(self.job_config, 'max_synthesis')

    def max_summon_special(self):
        """max special drops in exp_ball, if not set, 4 by default"""
        return safe_get(self.job_config, 'max_summon_special')

    def target_summon_special(self):
        """specify which special drop to count for max_summon_special, name of imgs in summon_special"""
        return safe_get(self.job_config, 'target_summon_special')

    def disable_burning(self):
        """disable the servant and command code burning in exp_ball, this will cause the servant position quick filled up.
        should only be used when you need more low star servants to maximum Hogu"""
        return safe_get(self.job_config, 'disable_burning')
    
    def exp_only(self):
        """exp_ball go to the exp_only mode, will by defaul sell all un relavant fou and resiou"""
        return safe_get(self.job_config, 'exp_only')

    def reisou_burn_min_star(self):
        """max stars when selecting reisous to burn"""
        return safe_get(self.job_config, 'reisou_burn_min_star')

    def code_burn_max_star(self):
        """max stars when selecting command code to burn"""
        return safe_get(self.job_config, 'code_burn_max_star')

    def use_preset(self):
        """using any of the preset config in the presets section"""
        return safe_get(self.job_config, 'use_preset')

    def turns(self):
        """turns config"""
        return safe_get(self.job_config, 'turns')

    def use_pot(self):
        """use the kp teapot"""
        return safe_get(self.job_config, 'use_pot')

    def force_turns(self):
        """force the turn config to finish, not turn to xjbd if the turn > stage"""
        return safe_get(self.job_config, 'force_turns')
    
    def second_pos(self):
        """second position in the chapter menu"""
        return safe_get(self.job_config, 'second_pos')
    
    def goto(self):
        """quest to goto"""
        return safe_get(self.job_config, 'goto')