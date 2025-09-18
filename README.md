<h1 align="center">
  <br>
  <a href="https://battlebanana.xyz"><img width="25%" src="https://github.com/DeveloperAnonymous/BattleBanana/blob/master/botimg/battlebanana_transparent.png" alt="BattleBanana"></a>
  <br>
  BattleBanana Discord Bot
  <br>
</h1>

<p align="center">
  <strong>The questing and RPG/roleplaying bot</strong><br>
  <a href="https://discord.gg/xCgnHzW">
    <img src="https://discordapp.com/api/guilds/431932271604400138/widget.png" alt="Discord Server">
  </a>
  <a href="https://patreon.com/developeranonymous">
    <img src="https://img.shields.io/badge/Donate-Patreon-F96854.svg?logo=patreon" alt="Support Us">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Made%20With-Python%203.13-blue.svg?style=for-the-badge" alt="Made with python">
  </a>
  <a href="https://makeapullrequest.com">
    <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="Discord Server">
  </a>
  <a href="https://top.gg/bot/464601463440801792">
    <img src="https://discordbots.org/api/widget/servers/464601463440801792.svg" alt="Discord Bots">
  </a> <br>
  <a href="https://www.gnu.org/licenses/gpl-3.0.en.html">
      <img src="https://img.shields.io/github/license/developeranonymous/battlebanana" alt="GPL 3.0">
  </a>
  <a href="https://github.com/Rapptz/discord.py/">
      <img src="https://img.shields.io/badge/discord-py-blue.svg" alt="discord.py">
  </a>
  <a href="https://battlebanana.xyz/">
      <img alt="Website" src="https://img.shields.io/website?down_message=Offline&label=battlebanana.xyz&up_color=bright-green&up_message=Online&url=https%3A%2F%2Fbattlebanana.xyz">
  </a>
  <br>
  <a href="https://www.digitalocean.com/?refcode=4e8f4d74dfa5&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge">
    <img src="https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%201.svg" alt="DigitalOcean Referral Badge" />
  </a>
</p>

## Overview

BattleBanana can be a fun addition to your server allowing you to create customizable quests and weapons, giving your
players the ability to fight those quests or eachother to gain EXP, stats and cash. It does not promise to provide you
anything useful but you may be able to have some fun with it

### Features

BattleBanana has many feature like

- Creating your own custom quests and weaponary
- Battling your friends to decide whos the best of you, or become the top player of BattleBanana by fighting others to
  become the TopDog
- Creating your own team for you and your friends
- Customizable profiles to show off your own style
- Trying your luck with gambling your cash

For more information on how to use the bot you can look at our ["how to"](https://battlebanana.xyz/howto/) guide!

## Join our community

BattleBanana is still being developed with an active community behind it and supporting its development, you too can
help its development by joining [our server](https://battlebanana.xyz/support)
, [contribute](https://github.com/DeveloperAnonymous/BattleBanana#Contribute) towards the source code,
or [donating](https://patreon.com/developeranonymous) to help pay for server costs

## Contribute

If you have a solid understanding of python, you can help BattleBanana by contributing towards the source code by fixing
bugs, adding new features or fixing up the repo.

## Hosting

You can host BattleBanana yourself in a few easy steps

1. Make sure you have [Docker](https://docs.docker.com/get-docker/) installed
2. Clone this repository `git clone https://github.com/BattleBanana/BattleBanana.git`
3. Rename and edit the example config files:
    1. `battlebanana.example.json` -> `battlebanana.json`
    2. `dbconfig.example.json` -> `dbconfig.json`
    3. `generalconfig.example.json` -> `generalconfig.json`
4. Edit the database configuration in `docker-compose.yml` to match your `dbconfig.json` file
5. Run `docker-compose up -d --build` to build and start the bot

## License

Licensed under [GPL 3.0](https://www.gnu.org/licenses/gpl-3.0.en.html)
