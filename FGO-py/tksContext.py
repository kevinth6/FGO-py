import copy
from tksCommon import FlowException


class TksContext:
    def __init__(self, config, account):
        self.config = config
        self.account = account
        self._setup_jobs_config(config, account)
        self._setup_job_contexts()
        self.current_job = None
        self.options_checked = False

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
            self.job_contexts[job] = TksJobContext(self)

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

    def save(self):
        pass

    def load(self):
        pass

    @staticmethod
    def anonymous_context():
        config = {'accounts': ['anonymous'], 'all_jobs': [{'name': 'random-job'}]}
        ret = TksContext(config, 'anonymous')
        ret.current_job = 'random-job'
        return ret


class TksJobContext:
    def __init__(self, context):
        self.context = context
        self.apple_used = 0
        self.battle_completed = 0
        self.battle_failed = 0
        self.total_turns = 0
        self.total_time = 0
        self.material = {}

    def apple_remaining(self):
        apple_total = (self.context.cur_job_config()['apples']) if 'apples' in self.context.cur_job_config() else 0
        return self.apple_used < apple_total
