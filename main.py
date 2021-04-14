import argparse
import json
import os
from steam.client import SteamClient

from const import LANGUAGES

import requests
import tqdm

DISPLAY_WIDTH = 60


def check_appid(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("%s should be a positive value" % value)
    return ivalue


parser = argparse.ArgumentParser(description='Fetch Steam Rich-Presence Tokens')
parser.add_argument('-u', dest='username', action='store', help='username')
parser.add_argument('-p', dest='password', action='store', help='password')
parser.add_argument('-f', dest='appid_from', type=check_appid,
                    action='store', help='from appid', default=-1)
parser.add_argument('-t', dest='appid_to', type=check_appid,
                    action='store', help='to appid', default=-1)

args = parser.parse_args()

client = SteamClient()
client.cli_login(args.username, args.password)

print("Logged on as: %s" % client.user.name)


def process_token(app_id, token_lists, from_language):
    for token_list in token_lists:
        if token_list.language != from_language:
            continue
        tokens_map = {}
        for token in token_list.tokens:
            tokens_map[token.name] = token.value
        json.dump(
            tokens_map,
            open(f"tokens/{app_id}/{token_list.language}.json", "w+"),
            indent=2, ensure_ascii=False
        )


appid_list = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/").json()
apps = appid_list["applist"]["apps"]
apps = list(filter(lambda x: x["appid"] % 10 == 0, apps))  # remove non-apps
apps.sort(key=lambda x: x["appid"])
if args.appid_from > 0:
    apps = list(filter(lambda x: x["appid"] >= args.appid_from, apps))
if args.appid_to > 0:
    apps = list(filter(lambda x: x["appid"] <= args.appid_to, apps))

with tqdm.tqdm(apps) as t:
    for app in t:
        formatted_name = app["name"].ljust(DISPLAY_WIDTH, " ")[:DISPLAY_WIDTH]
        t.set_description(f'{app["appid"]} - {formatted_name}')
        app_id = app["appid"]
        response = client.send_um_and_wait('Community.GetAppRichPresenceLocalization#1', {
            'appid': app_id,
            'language': "english",
        })
        if response:
            if len(response.body.token_lists):
                os.makedirs(f"tokens/{app_id}", exist_ok=True)
                process_token(app_id, response.body.token_lists, "english")
                with tqdm.tqdm(LANGUAGES, desc='Languages') as tlang:
                    for language in tlang:
                        tlang.set_description(language.ljust(20))
                        response = client.send_um_and_wait('Community.GetAppRichPresenceLocalization#1', {
                            'appid': app_id,
                            'language': language,
                        })
                        process_token(app_id, response.body.token_lists, language)

client.logout()
