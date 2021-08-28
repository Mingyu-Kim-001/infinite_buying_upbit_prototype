import requests

class Slack_bot:
    def __init__(self, token, channel, is_dev=False):
        self.token = token
        self.channel = channel
        self.is_dev = is_dev

    def post_message(self, *texts):
        channel, token = self.channel, self.token
        text = " ".join([str(text) for text in texts])

        if self.is_dev:
            print(text)
            return

        response = requests.post("https://slack.com/api/chat.postMessage",
                                 headers={"Authorization": "Bearer " + token},
                                 data={"channel": channel, "text": text}
                                 )