def get_data_location_base_dir() -> str:
    # Airflow ホスト上の入力ベース（FileSensor がパーティション出現を検知する）
    data_dir = '/tmp/dedp/incremental_loader/input'
    return data_dir

def get_data_output_base_dir() -> str:
    # Spark ジョブ（Pod）が参照するコンテナ側の出力ベース。
    # ホスト /tmp/dedp/incremental_loader は minikube mount で /data_for_demo にマップされる。
    # 出力先は Spark の overwrite が生成するため、ここでの mkdir は不要。
    data_dir = '/data_for_demo/output'
    return data_dir

def get_namespace() -> str:
    return 'dedp-demo'
