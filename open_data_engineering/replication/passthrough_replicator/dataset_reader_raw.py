from pyspark.sql import SparkSession

from config import DemoConfiguration

if __name__ == "__main__":
    spark_session = SparkSession.builder.master("local[*]").getOrCreate()

    input_dataset = (
        spark_session.read
        .format('json')
        .load(DemoConfiguration.OUTPUT_PATH)
    )

    input_dataset.show(truncate=False, n=4)