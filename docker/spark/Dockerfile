FROM apache/spark:3.5.1

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV SPARK_KAFKA_PACKAGE=org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        python3-pip \
        tshark \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir \
        joblib \
        numpy \
        pandas \
        scipy \
        scikit-learn

RUN mkdir -p /tmp/.ivy2 \
    && printf '%s\n' \
        'from pyspark.sql import SparkSession' \
        'spark = SparkSession.builder.appName("resolve-kafka-connector").getOrCreate()' \
        'spark.stop()' \
        > /tmp/resolve_kafka_connector.py \
    && /opt/spark/bin/spark-submit \
        --master local[1] \
        --conf spark.jars.ivy=/tmp/.ivy2 \
        --packages "${SPARK_KAFKA_PACKAGE}" \
        /tmp/resolve_kafka_connector.py \
    && find /tmp/.ivy2/jars -type f -name '*.jar' -exec cp {} /opt/spark/jars/ \; \
    && test -f /opt/spark/jars/org.apache.spark_spark-sql-kafka-0-10_2.12-3.5.1.jar \
    && rm -rf /tmp/.ivy2 /tmp/resolve_kafka_connector.py

USER spark

RUN tshark -v >/dev/null
