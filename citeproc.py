import subprocess
from datetime import datetime


class CiteProc:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

        self.init_commands = ['screen -S serve_npm -d -m bash -c "npm start"',
                              'sleep 2']

        for shell_script in self.init_commands:
            subprocess.call(shell_script, shell=True, cwd=self.config.citeproc_js_server_directory)

        self.logger.info('Started citeproc-js-server')

    def shutdown(self):
        shutdown_commands = ['screen -S serve_npm -X quit']

        for shell_script in shutdown_commands:
            subprocess.call(shell_script, shell=True)

        self.logger.info('Shutdown citeproc-js-server')
