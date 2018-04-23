# -*- coding: utf-8 -*-

import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import json
from configparser import ConfigParser

parser = ConfigParser()
parser.read('config.ini')

db_name = parser.get('Redshift', 'db_name')
host = parser.get('Redshift', 'host')
port = parser.get('Redshift', 'port')
username = parser.get('Redshift', 'username')
pwd = parser.get('Redshift', 'pwd')


conn_string = 'postgresql://' + username + ':' + pwd + '@' + host + ':' + port + '/' + db_name
engine = create_engine(conn_string).connect()
print('connected to Redshift')

# with open('sql-queries.json') as sql_file:
#     sql_data = json.load(sql_file)
#     for query_data in sql_data:
#         query, name = query_data['sql'], query_data['name']
#         print('fetching query results for ' + name)
#         data_frame = pd.read_sql_query(query, engine)
#         print(str(data_frame.shape[0]) + ' rows found')
#         print('writing .csv')
#         data_frame.to_csv(temp_file_dir + name, index=False)
#         print('wrote ' + name)
#         break
query = "select nspname from pg_namespace WHERE nspname NOT LIKE 'pg%%' AND nspname NOT IN ('logs', 'public', 'information_schema') ORDER BY nspname asc;"
data_frame = pd.read_sql_query(query, engine)
print(data_frame)
