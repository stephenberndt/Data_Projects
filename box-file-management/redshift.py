#!/Users/sberndt/anaconda3/bin/python

from sqlalchemy import create_engine
import pandas as pd
from configparser import ConfigParser
import csv
import re


class Redshift(object):

    def __init__(self):
        parser = ConfigParser()
        parser.read('config.ini')
        self.db_name = parser.get('Redshift', 'db_name')
        self.host = parser.get('Redshift', 'host')
        self.port = parser.get('Redshift', 'port')
        self.username = parser.get('Redshift', 'username')
        self.pwd = parser.get('Redshift', 'pwd')
        self.query = None
        self.data_frame = None
        try:
            self.conn_string = 'postgresql://' + self.username + ':' + self.pwd + '@' + self.host + ':' + self.port + '/' + self.db_name
            self.engine = create_engine(self.conn_string).connect()
            print('connected to Redshift')
        except TimeoutError:
            print('unable to connect to Redshift')

    def run_sql_return(self, query_string):
        """
        Run SQL and return the results of the query in a data frame
        :param query_string: SQL query
        :return: data frame containing the contents of the query
        """
        self.query = query_string
        self.data_frame = pd.read_sql_query(self.query, self.engine)
        print(str(self.data_frame.shape[0]) + ' rows found')
        return self.data_frame

    def run_sql_no_return(self, query_string):
        """
        Run SQL and do not return the results of the query
        :param query_string: SQL Query
        """
        self.query = query_string
        self.engine.execute(self.query)


def multiple_replace(dict_trans, text_string):
    """
    Use a regular expression to translate a dictionary of keys
    :param dict_trans: dict of key value translations
    :param text_string: string to perform translations on
    :return: translated string
    """
    regex = re.compile("(%s)" % "|".join(map(re.escape, dict_trans.keys())))
    # For each match, look-up corresponding value in dictionary
    return regex.sub(lambda mo: dict_trans[mo.string[mo.start():mo.end()]], text_string)


def translate_roku_tracker(start_string, end_string):
    """
    Created to translate the tracker value in the RMF
    :param start_string:
    :param end_string:
    """
    print(start_string.lower())
    substitutions = {
        "install now": "homepagebanner",
        "watch now": "homepagebanner",
        " - ": "_",
        "tlc go": "tlc_prom",
        "investigation discovery go": "id_prom",
        "discovery go": "dsc_prom",
        "__": "_",
        " ": ""
    }
    tracker_name = multiple_replace(substitutions, start_string.lower())
    print(tracker_name)
    tracker_name_list = tracker_name.split('_')
    tracker_name_list[3], tracker_name_list[2] = tracker_name_list[2], tracker_name_list[3]
    print(tracker_name_list)
    tracker_name_new = ""
    for item in tracker_name_list:
        tracker_name_new = tracker_name_new + str(item) + "_"
    print(tracker_name_new[:-1])
    print(end_string.lower().replace(" ", ""))


def update_daily_go_roi():
    """
    Update the daily go roi dashboard
    """
    with open('insert_go_spend_daily.csv') as newRows:
        reader = csv.reader(newRows)
        query = "insert into sberndt.roi_spend_raw values "
        row_list = []
        for index, row in enumerate(reader, start=1):
            # Clean up the strings from how they are read out of the csv by Python
            clean_row = str(row[0:5])[2:-2].replace('"', '')
            clean_row = re.sub("\)$", "')", clean_row)
            # Add each cleaned row to a list
            row_list.append(clean_row)
            # Create a list of 500 rows and upload once there are 500
            if len(row_list) == 500:d
                row_list = str(row_list).translate({ord(i): None for i in '[]"'})
                print(query + row_list)
                rs.run_sql_no_return(query + row_list)
                # Reset the list
                row_list = []
        # This needs to take the last part of the file that was less that 500 entries and insert it into the table
        row_list = str(row_list).translate({ord(i): None for i in '[]"'})
        print(query + row_list)
        rs.run_sql_no_return(query + row_list)


def update_roku_daily_roi():
    with open('insert_roku_spend_daily.csv') as newRows:
        # rs.run_sql_no_return("TRUNCATE table data_strategy.roku_spend_daily_test")
        reader = csv.reader(newRows)
        # query = "insert into data_strategy.roku_spend_daily values "
        query = "insert into data_strategy.roku_spend_daily values "
        row_list = []
        next(reader, None)
        for index, row in enumerate(reader, start=1):
            show_details = row[3].split("_")
            try:
                show_name = show_details[3]
                promo_type = show_details[2]
            except IndexError:
                show_name = ""
                promo_type = ""
            row.insert(3, show_name)
            row.insert(2, promo_type)
            row = str(row).replace('[', '(')
            row = row.replace(']', ')')
            row_list.append(row)
            if len(row_list) == 200:
                for entry in row_list:
                    query = query + entry.replace("\\", "") + ", "
                    query = re.sub("\)'", ")", query)
                    query = re.sub("'\(", "(", query)
                    query = re.sub("\"", "'", query)
                    query = re.sub("(?<=[a-zA-Z])'(?=[a-zA-Z])", r"\'", query)
                rs.run_sql_no_return(query[:-2])
                print(query[:-2])
                row_list = []
                query = "insert into data_strategy.roku_spend_daily values "
        for entry in row_list:
            query = query + entry.replace("\\", "") + ", "
            query = re.sub("\)'", ")", query)
            query = re.sub("'\(", "(", query)
            query = re.sub("\"", "'", query)
            query = re.sub("(?<=[a-zA-Z])'(?=[a-zA-Z])", r"\'", query)
        rs.run_sql_no_return(query[:-2])
        print(query[:-2])


if __name__ == '__main__':
    rs = Redshift()
    update_daily_go_roi()
    # update_roku_daily_roi()
    # with open('roi-refresh.sql', 'r') as sql_file:
    #     contents = sql_file.read()
    #     print(contents)

        # rs.run_sql_no_return(contents)

    print('finished')
