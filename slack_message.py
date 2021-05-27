import requests
class Slack_bot:
    def __init__(self, token, channel):
        self.token = token
        self.channel = channel

    def post_message(self,*texts):
        channel, token = self.channel, self.token
        text = [str(text) for text in texts]
        response = requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer " + token},
            data={"channel": channel,"text": text}
        )