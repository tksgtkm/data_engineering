import os
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
from airflow.providers.cncf.kubernetes.sensors.spark_kubernetes import SparkKubernetesSensor
from airflow.providers.standard.sensors.filesystem import FileSensor

from config import get_data_location_base_dir, get_data_output_base_dir, get_namespace

with DAG(
    'visits_incremental_loader', 
    max_active_runs=1,
    default_args={
        'depends_on_past': True,
        'start_date': pendulum.parse("2023-11-01"),
        'end_date': pendulum.parse("2023-11-06"),
        'retries': 3,
        'retry_delay': timedelta(minutes=1)
    },
    template_searchpath=[os.getcwd()],
    schedule="@daily",
    user_defined_macros={
        'output_base_dir': get_data_output_base_dir(),  # /data_for_demo/output
        'job_namespace': get_namespace(),               # dedp-demo
    },
) as dag:
    next_partition_template = get_data_location_base_dir() + '/date={{ data_interval_end | ds }}'
    current_partition_template = get_data_location_base_dir() + '/date={{ ds }}'

    next_partition_sensor = FileSensor(
        task_id='next_partition_sensor',
        filepath=next_partition_template,
        mode='reschedule',
        do_xcom_push=False
    )

    load_job_trigger = SparkKubernetesOperator(
        task_id='load_job_trigger',
        namespace=get_namespace(),
        application_file='visits_incremental_loader.yaml',
        do_xcom_push=True
    )

    load_job_sensor = SparkKubernetesSensor(
        task_id='load_job_sensor',
        namespace=get_namespace(),
        mode='reschedule',
        application_name="{{ task_instance.xcom_pull(task_ids='load_job_trigger')['metadata']['name'] }}",
        attach_log=True
    )

    next_partition_sensor >> load_job_trigger >> load_job_sensor