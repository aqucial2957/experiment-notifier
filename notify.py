# coding: utf-8
from datetime import timedelta
import functools
from logging import getLogger
import os
import re
import sys
import time
from typing import Callable, Dict, Iterable, Optional, TypeVar, Union

import slack
from slack.errors import SlackApiError

logger = getLogger(__name__)

T = TypeVar('T')


def _is_valid_mention(s: str) -> bool:
    # channel, here, or U...
    valid_str = r'channel|here|U[0-9A-Z]+'
    return re.match(valid_str, s) is not None


class notify:
    """Sends a notification to Slack when the decolated function has been
    finished executing.

    Args:
        channel (str): Channel where the message will be sent.
        mentions (str or Iterable[str], optional): User id(s) to be mentioned.
        `channel`, `here`, or user id (`U...`) is acceptable. Defaults to None.
        token (str, optional): A string that specifies bot token. If set to
        None, the value of `os.environ['SLACK_API_TOKEN']` is used. Defaults to
        None.

    Examples:
        >>> from notify import notify
        >>> @notify('#general', mentions='channel')
        ... def main():
        ...     pass
        >>> main()  # notification will be sent to the '#general' channel

    Note:
        It is necessary to add the scope `chat:write` to the token.
    """

    def __init__(self, channel: str,
                 mentions: Optional[Union[str, Iterable[str]]] = None,
                 token: Optional[str] = None) -> None:
        # channel where message is sent
        self.channel = channel

        # mentions
        if mentions is None:
            self.mentions = []
        elif isinstance(mentions, str):
            self.mentions = [mentions]
        else:
            self.mentions = list(mentions)

        for mention in self.mentions:
            if not _is_valid_mention(mention):
                raise ValueError(
                    f"Mention '{mention}' is not valid. Only 'channel', "
                    "'here', or user id ('U...') is acceptable."
                )

        # slack api token
        if token is None:
            token = os.environ['SLACK_API_TOKEN']
        self.token = token

        self.error = None

        # start & end times
        self.t_start = None
        self.t_end = None

        self.func_name = None

    def __call__(self, f: Callable[..., T]) -> Callable[..., T]:
        self.func_name = f.__name__

        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> T:
            self.t_start = time.time()

            try:
                res = f(*args, **kwargs)
            except Exception as e:
                self.t_end = time.time()
                self.error = e
                self._send()
                raise
            else:
                self.t_end = time.time()
                self._send()

            return res

        return wrapper

    def _send(self) -> int:
        client = slack.WebClient(token=self.token)
        message = self._create_message()

        logger.debug('Sending a notification to Slack.')

        try:
            response = client.chat_postMessage(**message)
        except SlackApiError as e:
            logger.error(f'Could not send a notification: {e}')
            status = 1
        else:
            logger.debug(response)
            status = 0

        return status

    def _create_message(self) -> Dict[str, str]:

        # --- main text --- #
        # mentions
        prefix = ' '.join([f'<!{s}>' if s == 'channel' or s == 'here'
                           else f'<@{s}>' for s in self.mentions])
        msg = "Execution succeeded!" if self.error is None \
            else "Execution failed!"
        text = f"{prefix} *{msg}* (at function `{self.func_name}`)"

        # --- attachments --- #
        # i) command
        command_name = ' '.join([os.path.basename(sys.executable)] + sys.argv)
        command = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Command*```{command_name}```"
            }
        }

        # ii) time elapsed
        dt = timedelta(seconds=(self.t_end - self.t_start))
        time_elapsed = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Time elapsed*\n{str(dt)[:-3]}"
            }
        }

        # iii) error message
        if self.error is not None:
            error_msg = {
                # error message
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text":
                        f"*Error message*\n"
                        f"```{self.error.__class__.__name__}: {self.error}```"
                }
            }

        # iv) divider
        divider = {
            "type": "divider"
        }

        # v) footer
        footer = {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Sent from *notify.py* at {os.uname()[1]}"
                }
            ]
        }

        # in case of success
        if self.error is None:
            message = {
                "channel": self.channel,
                "text": text,
                "attachments": [
                    {
                        "fallback": "Details about the execution results.",
                        "color": "#36a64f",
                        "blocks": [command, time_elapsed, divider, footer]
                    }
                ]
            }
        # in case of failure
        else:
            message = {
                "channel": self.channel,
                "text": text,
                "attachments": [
                    {
                        "fallback": "Details about the execution results.",
                        "color": "#cf0301",
                        "blocks": [command, time_elapsed, error_msg,
                                   divider, footer]
                    }
                ]
            }

        return message
