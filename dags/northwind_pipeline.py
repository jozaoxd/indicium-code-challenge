import os
import csv
import psycopg2
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
from psycopg2 import sql
from contextlib import closing

# Configuration settings for the DAG
dag_config = {
    'owner': 'airflow_manager',
    'depends_on_past': False,
    'start_date': days_ago(0),
    'notify_on_failure': False,
    'notify_on_retry': False,
    'retries': 1,
    'retry_interval': timedelta(minutes=5),
}

# Define the DAG
pipeline = DAG(
    'etl_northwind',
    default_args=dag_config,
    description='Data pipeline for processing Northwind database',
    schedule_interval=timedelta(days=1),
)

def pull_data_pgsql(**kwargs):
    run_date = kwargs['ds']
    # Replace 'your_connection_name' with the actual connection name in Airflow
    db_hook = PostgresHook(postgres_conn_id='your_connection_name')
    db_conn_str = db_hook.get_uri()
    dest_folder = os.path.join(kwargs['AIRFLOW_HOME'], f"data/pgsql/{run_date}")
    if not os.path.isdir(dest_folder):
        os.makedirs(dest_folder)

    db_tables = ['categories', 'customers', 'employees', 'orders', 'products', 'shippers', 'suppliers']
    with closing(psycopg2.connect(db_conn_str)) as conn:
        with conn.cursor() as cursor:
            for table in db_tables:
                sql_query = sql.SQL("COPY (SELECT * FROM {}) TO STDOUT WITH CSV HEADER").format(sql.Identifier(table))
                csv_file_path = os.path.join(dest_folder, f"{table}.csv")
                with open(csv_file_path, 'w', newline='') as csv_file:
                    cursor.copy_expert(sql_query, csv_file)

def pull_data_csv(**kwargs):
    run_date = kwargs['ds']
    original_file = os.path.join(kwargs['AIRFLOW_HOME'], 'data/order_details.csv')
    dest_folder = os.path.join(kwargs['AIRFLOW_HOME'], f"data/csv/{run_date}")
    if not os.path.isdir(dest_folder):
        os.makedirs(dest_folder)
    dest_file = os.path.join(dest_folder, 'order_details_processed.csv')

    with open(original_file, 'r') as src_file, open(dest_file, 'w', newline='') as dest_file:
        csv_reader = csv.reader(src_file)
        csv_writer = csv.writer(dest_file)
        for data_row in csv_reader:
            csv_writer.writerow(data_row)

def insert_table_data(conn, csv_path, table_name):
    with open(csv_path, 'r') as file_obj:
        cur = conn.cursor()
        cur.copy_expert(f"COPY {table_name} FROM STDIN WITH CSV HEADER", file_obj)
        conn.commit()
        cur.close()

def push_data_pgsql(**kwargs):
    run_date = kwargs['ds']
    db_hook = PostgresHook(postgres_conn_id='your_connection_name')
    db_conn = db_hook.get_conn()
    
    # Process data for each table
    db_tables = ['categories', 'customers', 'employees', 'orders', 'products', 'shippers', 'suppliers']
    for table in db_tables:
        csv_path = os.path.join(kwargs['AIRFLOW_HOME'], f"data/pgsql/{run_date}/{table}.csv")
        insert_table_data(db_conn, csv_path, table)

    # Process 'order_details'
    details_path = os.path.join(kwargs['AIRFLOW_HOME'], f"data/csv/{run_date}/order_details_processed.csv")
    insert_table_data(db_conn, details_path, 'order_details')

    db_conn.close()

# Define DAG tasks
task_pull_pgsql = PythonOperator(
    task_id='pull_pgsql_data',
    python_callable=pull_data_pgsql,
    op_kwargs={'execution_date': '{{ ds }}'},
    dag=pipeline,
)

task_pull_csv = PythonOperator(
    task_id='pull_csv_data',
    python_callable=pull_data_csv,
    op_kwargs={'execution_date': '{{ ds }}'},
    dag=pipeline,
)

task_push_pgsql = PythonOperator(
    task_id='push_pgsql_data',
    python_callable=push_data_pgsql,
    op_kwargs={'execution_date': '{{ ds }}'},
    dag=pipeline,
)

# Set task dependencies
task_pull_pgsql >> task_pull_csv >> task_push_pgsql