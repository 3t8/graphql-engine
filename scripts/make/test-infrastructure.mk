# the following variables are set up in Docker Compose
# and are also defined in Harness.Constants for use in api tests
PG_PORT = 65002
PG_DBNAME = hasura
PG_DBUSER = hasura
PG_DBPASSWORD = hasura
MYSQL_PORT = 65001
MYSQL_DBNAME = hasura
MYSQL_DBUSER = hasura
MYSQL_DBPASSWORD = hasura
MSSQL_PORT = 65003
MSSQL_DBNAME = hasura
MSSQL_DBUSER = hasura
MSSQL_DBPASSWORD = Hasura1!
CITUS_PORT = 65004
DC_REFERENCE_PORT = 65005
DC_REFERENCE_AGENT_URL = localhost:$(DC_REFERENCE_PORT)/health
DC_SQLITE_PORT = 65007
DC_SQLITE_AGENT_URL = localhost:$(DC_SQLITE_PORT)/health
COCKROACH_PORT = 65008
COCKROACH_DBNAME = hasura
COCKROACH_DBUSER = root

# utils.sh contains functions used in CI to wait for DBs to be ready.
# this can be (ab)used like a script; e.g. `$(DB_UTILS) foo` expands to
# `source ./.buildkite/scripts/util/util.sh; foo`, which will run the `foo`
# function from util.sh (or anywhere else).
DB_UTILS = source ./.buildkite/scripts/util/util.sh;

# Use the Azure SQL Edge image instead of the SQL Server image on arm64.
# The latter doesn't work yet.
ifeq ($(shell uname -m),arm64)
MSSQL_IMAGE=mcr.microsoft.com/azure-sql-edge
else
MSSQL_IMAGE=  # allow the Docker Compose file to set the image
endif

# Run `sqlcmd` in a separate image when waiting for SQL Server to start.
MSSQL_SQLCMD = docker run --rm --platform=linux/amd64 --net=host mcr.microsoft.com/mssql-tools /opt/mssql-tools/bin/sqlcmd

export MSSQL_IMAGE
export MSSQL_SQLCMD

define stop_after
@ echo $1 >&2
@ $1 || EXIT_STATUS=$$?; \
if [[ -z "$${EXIT_STATUS:-}" ]]; then \
	$(MAKE) stop-everything; \
else \
	$(MAKE) stop-everything; \
	exit $$EXIT_STATUS; \
fi
endef

.PHONY: start-cockroach
## start-cockroach: start local PostgreSQL DB in Docker and wait for it to be ready
start-cockroach: spawn-cockroach wait-for-cockroach

.PHONY: spawn-cockroach
spawn-cockroach:
	docker compose up -d cockroach

.PHONY: wait-for-cockroach
wait-for-cockroach:
	$(DB_UTILS) wait_for_cockroach $(COCKROACH_PORT)
	$(DB_UTILS) wait_for_cockroach_db $(COCKROACH_PORT) "$(COCKROACH_DBNAME)" "$(COCKROACH_DBUSER)"

.PHONY: start-postgres
## start-postgres: start local PostgreSQL DB in Docker and wait for it to be ready
start-postgres: spawn-postgres wait-for-postgres

.PHONY: spawn-postgres
spawn-postgres:
	docker compose up -d postgres

.PHONY: wait-for-postgres
wait-for-postgres:
	$(DB_UTILS) wait_for_postgres $(PG_PORT)
	$(DB_UTILS) wait_for_postgres_db $(PG_PORT) "$(PG_DBNAME)" "$(PG_DBUSER)" "$(PG_DBPASSWORD)"

.PHONY: start-citus
## start-citus: start local Citus DB in Docker and wait for it to be ready
start-citus: spawn-citus wait-for-citus

.PHONY: spawn-citus
spawn-citus:
	docker compose up -d citus

.PHONY: wait-for-citus
wait-for-citus:
	$(DB_UTILS) wait_for_postgres $(CITUS_PORT)
	$(DB_UTILS) wait_for_postgres_db $(CITUS_PORT) "$(PG_DBNAME)" "$(PG_DBUSER)" "$(PG_DBPASSWORD)"

.PHONY: start-sqlserver
## start-sqlserver: start local MS SQL Server DB in Docker and wait for it to be ready
start-sqlserver: spawn-sqlserver wait-for-sqlserver

.PHONY: spawn-sqlserver
spawn-sqlserver:
	docker compose up -d sqlserver
	docker compose run sqlserver-init

.PHONY: wait-for-sqlserver
wait-for-sqlserver:
	$(DB_UTILS) wait_for_mssql $(MSSQL_PORT)
	$(DB_UTILS) wait_for_mssql_db $(MSSQL_PORT) "$(MSSQL_DBNAME)" "$(MSSQL_DBUSER)" "$(MSSQL_DBPASSWORD)"

.PHONY: start-mysql
## start-mysql: start local MariaDB in Docker and wait for it to be ready
start-mysql: spawn-mysql wait-for-mysql

.PHONY: spawn-mysql
spawn-mysql:
	docker compose up -d mariadb

.PHONY: wait-for-mysql
wait-for-mysql:
	$(DB_UTILS) wait_for_mysql $(MYSQL_PORT) "$(MYSQL_DBNAME)" "$(MYSQL_DBUSER)" "$(MYSQL_DBPASSWORD)"

.PHONY: start-dc-reference-agent
## start-dc-reference-agent: start the Data Connectors reference agent in Docker and wait for it to be ready
start-dc-reference-agent: spawn-dc-reference-agent wait-for-dc-reference-agent

.PHONY: spawn-dc-reference-agent
spawn-dc-reference-agent:
	docker compose up -d --build dc-reference-agent

.PHONY: wait-for-dc-reference-agent
wait-for-dc-reference-agent:
	$(DB_UTILS) wait_for_http_success $(DC_REFERENCE_AGENT_URL) "dc-reference-agent"

.PHONY: start-dc-sqlite-agent
## start-dc-sqlite-agent: start the Data Connectors SQLite agent in Docker and wait for it to be ready
start-dc-sqlite-agent: spawn-dc-sqlite-agent wait-for-dc-sqlite-agent

.PHONY: spawn-dc-sqlite-agent
spawn-dc-sqlite-agent:
	docker compose up -d --build dc-sqlite-agent

.PHONY: wait-for-dc-sqlite-agent
wait-for-dc-sqlite-agent:
	$(DB_UTILS) wait_for_http_success $(DC_SQLITE_AGENT_URL) "dc-sqlite-agent"

.PHONY: start-backends
## start-backends: start all known backends in Docker and wait for them to be ready
start-backends: \
	spawn-postgres spawn-sqlserver spawn-mysql spawn-citus spawn-dc-reference-agent spawn-dc-sqlite-agent spawn-cockroach \
	wait-for-postgres wait-for-sqlserver wait-for-mysql wait-for-citus wait-for-dc-reference-agent wait-for-dc-sqlite-agent wait-for-cockroach

.PHONY: stop-everything
## stop-everything: tear down test databases
stop-everything:
	# stop docker
	docker compose down -v

.PHONY: remove-tix-file
remove-tix-file:
	@ find . -name '*.tix' -delete
