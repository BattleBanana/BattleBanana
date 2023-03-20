#!/bin/bash
rm -rf ../BattleBanana.back
rsync -a . ../BattleBanana.back --exclude assets/imagecache/

echo "Backup created.. pulling latest updates"

git pull

find . -not -path "./logs/*" -exec chmod 755 {} \;
