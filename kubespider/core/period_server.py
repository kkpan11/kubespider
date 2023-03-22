import time
import os
import logging
import threading

from api import types
from core import download_trigger
from utils import helper
import source_provider.provider as sp

state_file_lock = threading.Lock()


class PeriodServer:
    def __init__(self, source_providers, download_providers) -> None:
        self.period_seconds = 3600
        self.source_providers = source_providers
        self.download_providers = download_providers
        self.state_file_dir = os.getenv('HOME') + '/.config'

    def run(self) -> None:
        while True:
            err = None
            for provider in self.source_providers:
                err = self.run_single_provider(provider)

            if err is None:
                time.sleep(self.period_seconds)
            else:
                time.sleep(20)

    def trigger_run(self, provider_name) -> None:
        for provider in self.source_providers:
            if provider_name != provider.get_provider_name():
                continue
            self.run_single_provider(provider)

    def trigger_run_all(self) -> None:
        for provider in self.source_providers:
            self.run_single_provider(provider)

    def run_single_provider(self, provider: sp.SourceProvider) -> TypeError:
        if provider.get_provider_type() != types.SOURCE_PROVIDER_PERIOD_TYPE:
            return None

        provider.load_config()
        links = provider.get_links("")
        link_type = provider.get_link_type()
        specific_download_provider = provider.get_download_provider()

        provider_name = provider.get_provider_name()
        state = self.load_state(provider_name)

        err = None
        for source in links:
            if helper.get_unique_hash(source['link']) in state:
                continue

            logging.info('Find new resource:%s/%s', provider_name, helper.format_long_string(source['link']))
            download_final_path = helper.convert_file_type_to_path(source['file_type']) + '/' + source['path']
            err = None
            if specific_download_provider is None:
                err = download_trigger.kubespider_downloader. \
                    download_file(source['link'],
                    download_final_path, link_type)
            else:
                err = download_trigger.kubespider_downloader. \
                    download_file(
                    source['link'], download_final_path, link_type, specific_download_provider)
            if err is not None:
                break
            state.append(helper.get_unique_hash(source['link']))

        self.save_state(provider_name, state)

        return err

    def load_state(self, provider_name) -> list:
        state_file_path = os.path.join(self.state_file_dir, 'state.cfg')
        all_state = helper.load_json_config(state_file_path, state_file_lock)
        if provider_name not in all_state.keys():
            return []
        return all_state[provider_name]

    def save_state(self, provider_name, state) -> None:
        state_file_path = os.path.join(self.state_file_dir, 'state.cfg')
        all_state = helper.load_json_config(state_file_path, state_file_lock)
        all_state[provider_name] = state
        helper.dump_json_config(state_file_path, all_state, state_file_lock)

kubespider_period_server = PeriodServer(None, None)
