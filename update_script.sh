#!/bin/bash
rm -rf ../BattleBanana.back
rsync -a . ../BattleBanana.back --exclude assets/imagecache/

echo "Backup created.. pulling latest updates"

git pull

chmod -R 755 *