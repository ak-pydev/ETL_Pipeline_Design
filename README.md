# Weather Kafka → Spark ETL

A small demo project that shows an end-to-end pipeline for ingesting weather CSV rows into Kafka, processing them with Spark Structured Streaming, and writing cleaned CSV output to mounted storage. The repository includes helper scripts and a Docker Compose setup for Kafka (Confluent), Zookeeper, and a small Spark cluster.

## What this project contains

- `docker-compose.yml` — Compose configuration for Zookeeper, Kafka, Spark master and workers, including volumes and health checks.
- `produce_messages.py` — Small Python script (kafka-python) that produces sample CSV rows to the `weather_raw` topic.
- `create_topic.bat`, `consume_topic.bat` — Convenience Windows batch wrappers to create and consume the `weather_raw` topic using the Kafka CLI inside the Kafka container.
- `spark-apps/process_weather.py` — Spark Structured Streaming job that reads from Kafka, parses CSV values, casts types, filters bad rows, and writes cleaned CSV to `/data/clean_weather` (mounted to the repo `./data` directory).
- `nifi_flow_settings.txt` — (Optional) NiFi credentials/settings generated for local use. Treat these as sensitive — rotate or secure as needed.
- `data/` — Local mount for checkpoints and cleaned output used by the Spark job.

## Architecture (high level)

1. Producers write plain-text CSV rows to Kafka topic `weather_raw`.
2. Spark Structured Streaming reads from `weather_raw` and parses rows into typed columns, producing `data/clean_weather` CSV outputs and writing offsets/checkpoints to `data/checkpoints/weather_etl`.
3. Optionally NiFi or other consumers can read from Kafka or from the cleaned files.

## Prerequisites

- Docker Desktop with Compose v2+ (Windows). Ensure Docker is running.
- Python 3.8+ if you plan to run `produce_messages.py` locally.
- Pip packages (only if running producer locally): `kafka-python`.

Install Python deps (optional):

```powershell
python -m pip install --user kafka-python
```

Notes about ports and listeners:
- The Kafka broker is configured to expose an EXTERNAL listener on port `9094` on the host. Inside the Docker network the broker listens on `9092`.
- When you run Kafka CLI commands inside the Kafka container (via `docker compose exec kafka ...`), use `localhost:9092` because that is the broker address inside the container.
- When you run a host-based producer/consumer (from your Windows host), use `localhost:9094` unless you change the broker advertised listeners.

## Quick start (PowerShell)

Open PowerShell in the repository root.

1) Start the stack

```powershell
# Start zookeeper, kafka, spark master/workers in background
docker compose up -d
```

2) Create the Kafka topic (runs the create command inside the kafka container)

```powershell
.\create_topic.bat
```

3) Produce sample messages

Option A — run the included Python producer on the host (recommended for quick tests):

- Edit `produce_messages.py` and set `bootstrap = 'localhost:9094'` (host → broker mapped port). Then:

```powershell
python .\produce_messages.py
```

Option B — run a producer inside a container that can reach Kafka internal listener `kafka:9092`.

4) Verify messages using the consumer wrapper (consumes from inside the kafka container)

```powershell
.\consume_topic.bat
```

5) Run the Spark streaming job (submit from the spark-master container)

```powershell
docker compose exec spark-master bash -lc "/opt/spark/bin/spark-submit --conf spark.jars.ivy=/tmp/.ivy2 --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.2 /opt/spark-apps/process_weather.py"
```

6) Check the cleaned output

After the Spark job runs, cleaned CSV files will appear under the `data/clean_weather` directory in the repository. You can list them in PowerShell:

```powershell
Get-ChildItem -Path .\data\clean_weather -File
Get-Content -Path .\data\clean_weather\part-* -TotalCount 20
```

## Important configuration notes & troubleshooting

- Bootstrap server mismatch: if your producer can't connect, double-check the bootstrap address. Host-based clients should use `localhost:9094` by default with this Compose file. Container-internal clients should use `localhost:9092` when executed inside the `kafka` container.

- Topic creation and CLI: `create_topic.bat` and `consume_topic.bat` run `docker compose exec kafka ...` which executes the Kafka CLI inside the Kafka container — this is why `--bootstrap-server localhost:9092` is used in the wrappers.

- Spark Kafka package: the `spark-submit` command includes the `spark-sql-kafka-0-10` package. If Spark fails to download packages inside the container, ensure outbound network access is available and increase the Ivy cache permissions if needed.

- Data directories: The Spark job writes to `/data/clean_weather` and checkpoint files to `/data/checkpoints/weather_etl`. The repo contains a `data/` mount. If the job fails due to missing dirs, create them on Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path .\data\clean_weather
New-Item -ItemType Directory -Force -Path .\data\checkpoints\weather_etl
```

- If Spark streaming doesn't pick up messages, confirm that the Spark job used the same topic (`weather_raw`) and check the `startingOffsets` option in `process_weather.py`.

## NiFi notes

- This repo contains `nifi_flow_settings.txt` (auto-generated username/password lines). Keep these values secure and rotate them if you publish or share this repo.

## Files of interest (quick)

- `spark-apps/process_weather.py` — main Spark job (reads Kafka, writes CSV).
- `produce_messages.py` — sample Python producer.
- `docker-compose.yml` — bring up Kafka, Zookeeper, and Spark cluster.
- `create_topic.bat` / `consume_topic.bat` — convenience wrappers.
- `data/clean_weather` — output directory for cleaned CSV; mounted into Spark containers.

## Suggestions / next steps

- Add a lightweight Docker image or service for the Python producer to avoid editing `produce_messages.py` when you want to run it from the network that can reach the internal Kafka listener.
- Add a small unit/integration test that verifies end-to-end flow locally (produce -> spark job processes -> file written).
- Secure the NiFi credentials and avoid committing secrets in public repos.

## License

This project is provided as-is for educational/demo purposes. Use at your own risk.
