import copy, time, yaml, os, collections, json
from tksCommon import FlowException, safe_get


class TksContext:
    def __init__(self, config, account):
        self.config = config
        self.account = account
        self.start_time = time.time()
        self._setup_jobs_config(config, account)
        self._setup_job_contexts()
        self.current_job = None
        self.battle_options_checked = False

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
                self.job_configs[job['name']].update(copy.deepcopy(job))

    def _setup_job_contexts(self):
        self.job_contexts = {}
        for job in self.job_configs:
            self.job_contexts[job] = TksJobContext(self.job_configs[job])

    def cur_job_config(self):
        if self.current_job and self.current_job in self.job_configs:
            return self.job_configs[self.current_job]
        else:
            raise FlowException("Can't get current job config, account: " + self.account + ", job: "
                                + self.current_job)

    def cur_job_context(self):
        if self.current_job and self.current_job in self.job_contexts:
            return self.job_contexts[self.current_job]
        else:
            raise FlowException("Can't get current job context, account: " + self.account + ", job: "
                                + self.current_job)

    def save(self, path='tksResult'):
        save_path = f"{path}/{self.account}"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        t = time.time()
        name = time.strftime(f'{save_path}{f"/res_%Y-%m-%d_%H.%M.%S.{round(t * 1000) % 1000:03}"}.json')
        with open(name, "w") as f:
            json.dump(self.out(), f, indent=4)

    def out(self):
        total_comp = TksContext.sum_in_obj_dict(self.job_contexts, 'battle_completed')
        total_fail = TksContext.sum_in_obj_dict(self.job_contexts, 'battle_failed')
        materials = {}
        for jck in self.job_contexts:
            TksContext.dict_add(materials, self.job_contexts[jck].materials)

        ret = collections.OrderedDict()
        ret["start_time"] = time.strftime(f'%Y-%m-%d_%H.%M.%S.{round(self.start_time * 1000) % 1000:03}')
        ret['end_time'] = time.strftime(f'%Y-%m-%d_%H.%M.%S.{round(self.start_time * 1000) % 1000:03}')
        ret['battle_completed'] = total_comp
        ret['battle_failed'] = total_fail
        ret['apple_used'] = TksContext.sum_in_obj_dict(self.job_contexts, 'apple_used')
        ret['total_turns'] = TksContext.sum_in_obj_dict(self.job_contexts, 'total_turns')
        ret['total_time'] = TksContext.sum_in_obj_dict(self.job_contexts, 'total_time')
        ret['avg_turns'] = TksContext.avg(TksContext.sum_in_obj_dict(self.job_contexts, 'total_turns'),
                                          total_comp + total_fail)
        ret['avg_time'] = TksContext.avg(TksContext.sum_in_obj_dict(self.job_contexts, 'total_time'),
                                         total_comp + total_fail)
        ret['special_drops'] = TksContext.sum_in_obj_dict(self.job_contexts, 'special_drops')
        ret['materials'] = materials

        return ret

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
        self.apple_used = 0
        self.battle_completed = 0
        self.battle_failed = 0
        self.total_turns = 0
        self.total_time = 0
        self.special_drops = 0
        self.materials = {}
        self.campaign_friend_checked = False

    def apple_remaining(self):
        return self.apple_used < self.apples()

    def apples(self):
        return safe_get(self.job_config, 'apples')

    def skip_main(self):
        return safe_get(self.job_config, 'skip_main')

    def team_index(self):
        return safe_get(self.job_config, 'team_index')

    def easy_mode(self):
        return safe_get(self.job_config, 'easy_mode')

    def chapter(self):
        return safe_get(self.job_config, 'chapter')

    def section(self):
        return safe_get(self.job_config, 'section')

    def instance(self):
        return safe_get(self.job_config, 'instance')

    def level(self):
        return safe_get(self.job_config, 'level')

    def cls(self):
        return safe_get(self.job_config, 'cls')

    def campaign_servant(self):
        return safe_get(self.job_config, 'campaign_servant')

    def campaign_reisou(self):
        return safe_get(self.job_config, 'campaign_reisou')

    def campaign_reisou_idx(self):
        return safe_get(self.job_config, 'campaign_reisou_idx')

    def friend_reisou(self):
        return safe_get(self.job_config, 'friend_reisou')

    def friend_class(self):
        return safe_get(self.job_config, 'friend_class')
