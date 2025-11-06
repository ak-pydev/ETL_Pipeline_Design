# Weather Kafka → Spark ETL

I built a small demo that shows how to move weather data from Kafka into Spark, clean it, and save the cleaned results as CSV files.

I wrote short scripts and a Docker Compose file so you can run Kafka, Zookeeper, and a Spark cluster locally.

## What I included

- `docker-compose.yml` — starts Zookeeper, Kafka, Spark master and workers.
- `produce_messages.py` — a small Python script that sends sample CSV rows to the `weather_raw` topic.
- `create_topic.bat`, `consume_topic.bat` — Windows helpers to create and read the `weather_raw` topic from the Kafka container.
- `spark-apps/process_weather.py` — Spark Structured Streaming job that reads Kafka, parses CSV, converts types, filters rows, and writes cleaned CSV to `/data/clean_weather`.
- `nifi_flow_settings.txt` — NiFi settings (contains generated credentials). Keep these private.
- `data/` — where cleaned files and checkpoints are stored (this is mounted into the Spark containers).

## Simple architecture

1. A producer (for example NiFi or `produce_messages.py`) writes plain CSV rows to Kafka topic `weather_raw`.
2. The Spark job (`process_weather.py`) reads from `weather_raw`, parses and cleans the rows, and writes CSV files to `data/clean_weather`.
3. You can use NiFi or other tools to pick up the cleaned files from `data/clean_weather`.

## What you need

- Docker Desktop (Compose v2+) on Windows. Make sure Docker is running.
- Python 3.8+ only if you want to run `produce_messages.py` from your machine.
- If you run the Python producer locally, install:

```powershell
python -m pip install --user kafka-python
```

## Quick start (PowerShell)

Open PowerShell in the repository folder and follow these steps.

1) Start the services

```powershell
docker compose up -d
```

2) Create the Kafka topic

```powershell
.\create_topic.bat
```

3) Send sample messages

Option A — from your Windows host (easy):

- Edit `produce_messages.py` and set `bootstrap = 'localhost:9094'` (host port). Then:

```powershell
python .\produce_messages.py
```

Option B — run a producer inside a container that can use the internal broker address `kafka:9092`.

4) See messages in the topic

```powershell
.\consume_topic.bat
```

5) Start the Spark job (run this inside the spark-master container)

```powershell
docker compose exec spark-master bash -lc "/opt/spark/bin/spark-submit --conf spark.jars.ivy=/tmp/.ivy2 --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.2 /opt/spark-apps/process_weather.py"
```

6) Check the cleaned output

When the Spark job runs, it writes cleaned CSV files to `data/clean_weather` in this repo. To check the files:

```powershell
Get-ChildItem -Path .\data\clean_weather -File
Get-Content -Path .\data\clean_weather\part-* -TotalCount 20
```

## Simple troubleshooting tips

- If a client (producer or consumer) cannot connect, check the bootstrap address:
	- From your Windows host use `localhost:9094` (this Compose file maps the broker to 9094).
	- If you run a client inside a container with the Compose network, use `kafka:9092`.
- If the Spark job fails to download Kafka packages, make sure the container has outbound internet access.
- If the Spark job cannot write files, create the data folders on Windows:

```powershell
New-Item -ItemType Directory -Force -Path .\data\clean_weather
New-Item -ItemType Directory -Force -Path .\data\checkpoints\weather_etl
```

## NiFi note (short)

I included `nifi_flow_settings.txt` with generated credentials for local testing. Treat those values as secrets and rotate them before sharing.

## Next steps I suggest

- Make a small container for the Python producer so you don't need to edit files to switch addresses.
- Add a simple test that produces rows, runs the Spark job, and checks that a cleaned file appears.

## License

This project is a simple demo for learning and teaching. Use it however you like.
