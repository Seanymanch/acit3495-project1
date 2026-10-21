#!/bin/sh
set -eu
export APP_PASS="$(cat /run/secrets/mongo_app_password)"
export READER_PASS="$(cat /run/secrets/mongo_reader_password)"
# Runs only when the Mongo data volume is first initialized, on localhost.
mongosh --quiet --host 127.0.0.1 --eval '
const analytics = db.getSiblingDB("analytics");
analytics.createUser({user: "analytics_app", pwd: process.env.APP_PASS, roles: [{role: "readWrite", db: "analytics"}]});
analytics.createUser({user: "analytics_reader", pwd: process.env.READER_PASS, roles: [{role: "read", db: "analytics"}]});
'
