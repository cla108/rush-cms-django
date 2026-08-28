#!/bin/bash

until nc -vz "$POSTGRES_DATABASE_HOST" "$POSTGRES_DATABASE_PORT"; do
  sleep 1
  echo "Waiting for Postgres at $POSTGRES_DATABASE_HOST:$POSTGRES_DATABASE_PORT"
done
echo "Postgres is available! Running main process..."
exec "$@"
