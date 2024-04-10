import pymysql
import json
import logging
import pandas as pd
import sqlalchemy as sql        # python3 -m pip install --upgrade 'sqlalchemy<2.0'
from sqlalchemy import create_engine, text

class mysql_class():
    def mysql_connect(self):
        # Load config from Json file.
        f = open('config.json')
        config_info = json.load(f)

        mysql_username = config_info["mysql_username"]
        mysql_password = config_info["mysql_password"]
        mysql_server   = config_info["remote_bind_adddress"]
        mysql_port     = config_info["mysql_port"]
        mysql_database = config_info["mysql_database"]
        
        connection = 'mysql://{}:{}@{}:{}/{}'.format(mysql_username,mysql_password,mysql_server,mysql_port,mysql_database)
        sql_engine = sql.create_engine(connection)
        
        return sql_engine, connection

    def run_query(self,sql,connection):
        """Runs a given SQL query via the global database connection.
        :param sql: MySQL query
        :return: Pandas dataframe containing results"""
        return pd.read_sql_query(sql, connection)

    def mysql_disconnect(self,connection):
        """Closes the MySQL database connection."""
        connection.close()