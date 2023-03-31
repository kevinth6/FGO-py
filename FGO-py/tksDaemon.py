import yaml, time, psutil, os, sys, subprocess

with open('tksDaemon.yaml', "r", encoding="utf-8") as f:
    daemonConf = yaml.load(f, Loader=yaml.FullLoader)


def find_pid(keyword):
    for proc in psutil.process_iter():
        if keyword in proc.name():
            return proc.pid


def list_processes():
    for proc in psutil.process_iter():
        print(proc)


def kill_proc(pid):
    os.system('taskkill /T /F /PID ' + str(pid))


def log(msg):
    time_str = time.strftime(f"%Y-%m-%d_%H:%M:%S:{round(time.time() * 1000) % 1000:03}")
    print(f'{time_str} - {msg}')


def run_script():
    for i in range(10):
        script_proc_path = daemonConf['script_proc_path']
        log(f"launch script. {script_proc_path}")
        subprocess.Popen(script_proc_path, cwd=daemonConf['working_folder'])
        j = 0
        while j < 3:
            # guarantee the script process steady running
            time.sleep(20)
            if not find_pid(daemonConf['script_proc_name']):
                log('Script failed to launch')
                break
            j += 1
        if j == 3:
            log('Script steady running')
            break


def main():
    run_interval = daemonConf['run_interval']
    check_interval = daemonConf['check_interval']

    last_run_time = None
    if len(sys.argv) >= 2:
        wait_time = int(sys.argv[1])
        last_run_time = time.time() - (run_interval - wait_time)

    while True:
        script_pid = find_pid(daemonConf['script_proc_name'])
        game_pid = find_pid(daemonConf['game_proc_name'])
        if script_pid and game_pid:
            log(f'Running. Game:{game_pid}, Script:{script_pid}')
            time.sleep(check_interval)
            continue

        if script_pid and not game_pid:
            log(f'Game not running, kill script proc {script_pid}')
            kill_proc(script_pid)
            time.sleep(5)
        elif game_pid and not script_pid:
            log(f'Script not running, kill game proc {game_pid}')
            kill_proc(game_pid)
            time.sleep(5)

        cur = time.time()
        exception = False
        if os.path.exists(daemonConf['stat_file']):
            log(f'Found stat file. recover from last stat.')
            exception = True

        if not last_run_time or cur - last_run_time > run_interval or exception:
            if script_pid:
                log('Already running. skip launch.')
            else:
                game_proc_path = daemonConf['game_proc_path']
                log(f"launch game. {game_proc_path}")
                subprocess.Popen(game_proc_path)
                time.sleep(30)
                run_script()
                if not exception or not last_run_time:
                    last_run_time = time.time()
                time_str = time.strftime(f"%Y-%m-%d_%H:%M:%S:{round(last_run_time * 1000) % 1000:03}")
                log(f'Finished launch. last run time: {time_str}')
        else:
            log(f'Idle. Launch after {run_interval - (cur - last_run_time):<.2f} seconds')

        time.sleep(check_interval)


main()
