#!/usr/bin/env python
# coding=utf-8

from sacred.observers.base import RunObserver, td_format
from sacred.config.config_files import load_config_file
import json


class MattermostObserver(RunObserver):
    """Sends a message to Mattermost upon completion/failing of an experiment."""

    @classmethod
    def from_config(cls, filename):
        """
        Create a MattermostObserver from a given configuration file.

        The file can be in any format supported by Sacred
        (.json, .pickle, [.yaml]).
        It has to specify a ``webhook_url`` and can optionally set
        ``bot_name``, ``icon``, ``completed_text``, ``interrupted_text``, and
        ``failed_text``.
        """
        return cls(**load_config_file(filename))

    def __init__(
        self,
        webhook_url,
        channel=None,
        bot_name="sacredbot",
        icon=":angel:",
        completed_text=None,
        interrupted_text=None,
        failed_text=None,
    ):
        """
        Create a Sacred observer that will send notifications to Mattermost.
        Parameters
        ----------
        webhook_url: str
            The webhook for the bot account.
        channel: str
            The channel to which to send notifications. To send direct messages, set to @username.
        bot_name: str
            The name of the bot.
        icon: str
            The icon of the bot.
        completed_text: str
            Text to be sent upoon completion.
        interrupted_text: str
            Text to be sent upon interruption.
        failed_text: str
            Text to be sent upon failure.
        """
        self.webhook_url = webhook_url
        self.bot_name = bot_name
        self.icon = icon
        self.completed_text = completed_text or (
            ":white_check_mark: *{experiment[name]}* "
            "completed after _{elapsed_time}_ with result=`{result}`"
        )
        self.interrupted_text = interrupted_text or (
            ":warning: *{experiment[name]}* " "interrupted after _{elapsed_time}_"
        )
        self.failed_text = failed_text or (
            ":x: *{experiment[name]}* failed after " "_{elapsed_time}_ with `{error}`"
        )
        self.run = None
        self.channel = channel

    def started_event(
        self, ex_info, command, host_info, start_time, config, meta_info, _id
    ):
        self.run = {
            "_id": _id,
            "config": config,
            "start_time": start_time,
            "experiment": ex_info,
            "command": command,
            "host_info": host_info,
        }

    def get_completed_text(self):
        return self.completed_text.format(**self.run)

    def get_interrupted_text(self):
        return self.interrupted_text.format(**self.run)

    def get_failed_text(self):
        return self.failed_text.format(**self.run)

    def completed_event(self, stop_time, result):
        import requests

        if self.completed_text is None:
            return

        self.run["result"] = result
        self.run["stop_time"] = stop_time
        self.run["elapsed_time"] = td_format(stop_time - self.run["start_time"])

        data = {
            "username": self.bot_name,
            "icon_emoji": self.icon,
            "text": self.get_completed_text(),
        }
        if self.channel is not None:
            data['channel'] = self.channel
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        requests.post(self.webhook_url, data=json.dumps(data), headers=headers)

    def interrupted_event(self, interrupt_time, status):
        import requests

        if self.interrupted_text is None:
            return

        self.run["status"] = status
        self.run["interrupt_time"] = interrupt_time
        self.run["elapsed_time"] = td_format(interrupt_time - self.run["start_time"])

        data = {
            "username": self.bot_name,
            "icon_emoji": self.icon,
            "text": self.get_interrupted_text(),
        }
        if self.channel is not None:
            data['channel'] = self.channel
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        requests.post(self.webhook_url, data=json.dumps(data), headers=headers)

    def failed_event(self, fail_time, fail_trace):
        import requests

        if self.failed_text is None:
            return

        self.run["fail_trace"] = fail_trace
        self.run["error"] = fail_trace[-1].strip()
        self.run["fail_time"] = fail_time
        self.run["elapsed_time"] = td_format(fail_time - self.run["start_time"])

        data = {
            "username": self.bot_name,
            "icon_emoji": self.icon,
            "text": self.get_failed_text(),
        }
        if self.channel is not None:
            data['channel'] = self.channel
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        requests.post(self.webhook_url, data=json.dumps(data), headers=headers)