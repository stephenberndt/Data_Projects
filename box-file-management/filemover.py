# -*- coding: utf-8 -*-

from boxsdk import Client, OAuth2
from os import listdir, rename
from datetime import datetime
from boto.s3.key import Key
from configparser import ConfigParser
import re
import json
import logging
import os
import plistlib
import requests
import smtplib
import sys
import boto
import boto.s3.connection


class FileMover(object):
    def __init__(self, s3_bucket, temp_dir, box_folder):
        parser = ConfigParser()
        parser.read('config.ini')
        self.oauth2URL = parser.get('Box', 'oauth2URL')
        self.apiURL = parser.get('Box', 'apiURL')
        self.authorizationCode = parser.get('Box', 'authorizationCode')
        self.clientId = parser.get('Box', 'clientId')
        self.clientSecret = parser.get('Box', 'clientSecret')
        self.box_folder_id = box_folder
        self.apiFolder = './'
        self.logFileFullPath = os.path.join(
            self.apiFolder, os.path.basename(os.path.abspath(__file__)) + '.log')
        self.plistFileFullPath = os.path.join(self.apiFolder, 'Box-API.plist')
        # AWS
        self.AWS_ACCESS_KEY_ID = parser.get('AWS', 'AWS_ACCESS_KEY_ID')
        self.AWS_SECRET_ACCESS_KEY = parser.get('AWS', 'AWS_SECRET_ACCESS_KEY')
        self.HOST = parser.get('AWS', 'HOST')
        self.bucket_name = s3_bucket
        self.conn = boto.connect_s3(self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY,
                                    host=self.HOST,
                                    is_secure=True,
                                    calling_format=boto.s3.connection.OrdinaryCallingFormat(),
                                    )
        # self.files_to_download = files_to_download
        self.temp_file_dir = temp_dir
        self.tempdir = os.getcwd() + "/" + self.temp_file_dir
        # Logging
        self.scriptName = os.path.basename(os.path.abspath(__file__))
        # Configure Logging
        logging.basicConfig(filename=self.logFileFullPath, level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s', filemode='w')
        # Kick off token generation when the class is initialized
        self.generate_tokens()

    def generate_tokens(self):
        """
        Genereates tokens to refresh authentication to Box. This must be done at least once every 2 months in order for the refresh token to be valid.
        """
        print('generating Box auth tokens')
        # Read this scripts plist
        try:
            # Read this scripts plist
            self.tokenPlist = plistlib.readPlist(self.plistFileFullPath)
            # Get the Refresh token from the plist
            self.refreshToken = self.tokenPlist["Refresh Token"]
        # If we can't find the plist
        except:
            # Try & generate new tokens
            try:
                # API call to generate tokens
                get_tokens = requests.post(self.oauth2URL, data={
                                           'grant_type': 'authorization_code', 'code': self.authorizationCode, 'client_id': self.clientId, 'client_secret': self.clientSecret})
                # If the above gives a 4XX or 5XX error
                get_tokens.raise_for_status()
                # Get the JSON from the above
                newTokens = get_tokens.json()
                # Get the new access token, valid for 60 minutes
                self.accessToken = newTokens['access_token']
                # Log the access token we're using
                logging.info('Generated Access Token: %s' % self.accessToken)
                # Get the refresh token, valid for 60 days
                self.refreshToken = newTokens['refresh_token']
                # Log the new refresh token we've generated
                logging.info('Generated Refresh Token: %s' % self.refreshToken)
                # Update plist with new refresh token & time generated, refresh
                # token used for subsequent runs
                plistlib.writePlist({'Refresh Token': self.refreshToken, 'Time Generated': datetime.now(
                ).isoformat(), }, self.plistFileFullPath)
                # Update tokenPlist variable
                tokenPlist = plistlib.readPlist(plistFileFullPath)
            # If we cannot generate the tokens
            except requests.exceptions.RequestException as e:
                # Status message to use as subject for sendMail funtion
                statusMessage = 'Cannot generate tokens %s' % e
                # Advise that no devices are to be deleted
                logging.error('-------- ' + statusMessage + ' --------')
                # Print the status
                print(statusMessage)
            # If we cannot create the plist
            except:
                # Status message to use as subject for sendMail funtion
                statusMessage = 'Cannot create plist'
                # Advise that no devices are to be deleted
                logging.error('-------- ' + statusMessage + ' --------')
                # Print the status
                print(statusMessage)
        # Try to make the API call
        try:
            # Log the token we're using & starting call
            logging.info('Using Refresh Token: %s' % self.refreshToken)
            # Get new access & refresh tokens
            get_tokens = requests.post(self.oauth2URL, data={
                                       'grant_type': 'refresh_token', 'refresh_token': self.refreshToken, 'client_id': self.clientId, 'client_secret': self.clientSecret})
            # If the above gives a 4XX or 5XX error
            get_tokens.raise_for_status()
            # Get the JSON from the above
            newTokens = get_tokens.json()
            # Get the new access token, valid for 60 minutes
            self.accessToken = newTokens['access_token']
            # Log the access token we're using
            logging.info('Generated Access Token: %s' % self.accessToken)
            # Get the refresh token, valid for 60 days
            self.refreshToken = newTokens['refresh_token']
            # Log the new refresh token we've generated
            logging.info('Generated Refresh Token: %s' % self.refreshToken)
            # Update plist with new refresh token & time generated, refresh
            # token used for subsequent runs
            plistlib.writePlist({'Refresh Token': self.refreshToken, 'Time Generated': datetime.now(
            ).isoformat(), }, self.plistFileFullPath)
            # Print the status
            print('successfully generated tokens')
        # If the API call fails, report error as e
        except requests.exceptions.RequestException as e:
            # Status message to use as subject for sendMail funtion
            statusMessage = 'Get request failed with %s' % e
            # Advise that no devices are to be deleted
            logging.error('-------- ' + statusMessage + ' --------')
            # Print the status
            print(statusMessage)

    @staticmethod
    def get_token():
        """
        Retrieves the token that was generated in the logs by generate_tokens()
        """
        print('retrieving refresh token')
        # Open the log file where the keys are kept
        with open(self.logFileFullPath) as token_log:
            # Check line 4 of the log file
            token_line = token_log.readlines()[3:4]
            # Change it from an array to a string
            token_string = token_line[0]
            # Return the new token with the /n removed
            return token_string[-33:].rstrip()

    def download_files_from_s3(self, files_to_download, s3_bucket=None):
        """
        Connect to an s3 bucket in order to download the files specified
        in the varialble files_to_download
        """
        if s3_bucket is None:
            bucket = self.conn.get_bucket(self.bucket_name)
        else:
            bucket = s3_bucket
        self.files_to_download = files_to_download
        print('s3 connection successful')
        print('downloading files from s3 folder - ' + str(bucket))
        if os.path.exists(self.tempdir):
            pass
        else:
            os.makedirs(self.tempdir)
            logging.info('Creating directory - {}'.format(self.tempdir))
        for filename in files_to_download:
            key = boto.s3.key.Key(bucket)
            key.key = filename
            key.get_contents_to_filename(self.tempdir + filename)
            print(filename + " downloaded")
            logging.info('Downloaded: {}'.format(self.tempdir + filename))
        print('download complete')

    def upload_files_to_s3(self, files_to_upload, s3_bucket=None):
        """
        Connect to an s3 bucket in order to upload the files specified in the variable
        files_to_upload
        """
        if s3_bucket is None:
            bucket = self.conn.get_bucket(self.bucket_name)
        else:
            bucket = s3_bucket
        self.files_to_upload = files_to_upload
        print('s3 connection successful')
        print('uploading files to s3 folder - ' + str(bucket))
        for filename in files_to_upload:
            key_name = filename
            key = bucket.new_key(self.tempdir + key_name)
            key.set_contents_from_filename(self.tempdir + key_name)
            print(filename + " uploaded")
        print('upload complete')

    def process_files(self, processFunction, files_to_process):
        """
        Use this to pass a function into the class to process the files in some way
        """
        return processFunction(self.temp_file_dir, files_to_process)

    def upload_to_box(self, files_to_upload, box_folder=None):
        """
        Uploads a list of files to Box based on the folder id specified when FileMover is initialized
        """
        oauth2 = OAuth2(self.clientId, self.clientSecret,
                        access_token=self.accessToken)
        client = Client(oauth2)
        my = client.user(user_id='me').get()
        print('connected to Box as ' + my.login)
        if box_folder is None:
            target_folder = client.folder(self.box_folder_id)
        else:
            target_folder = client.folder(box_folder)
        target_folder_info = target_folder.get()
        items_in_Box_folder = target_folder.get_items(limit=None, offset=0)

        for file_name in files_to_upload:
            # Check the Box folder to see if the files exist
            for item in items_in_Box_folder:
                # If the file does already exist, use update_contents
                if item.name == file_name:
                    box_file = item.update_contents(
                        self.temp_file_dir + file_name)
                    print(item.name + ' updated')
                    break
            # If the file did not exist, use upload
            if file_name not in set(files_to_upload):
                box_file = target_folder.upload(
                    self.temp_file_dir + file_name, file_name)
                print(file_name + ' uploaded')

            os.remove(self.temp_file_dir + file_name)

    def download_from_box(self, files_to_download, box_folder=None, use_dl_links=False):
        """
        Downloads a list of files from a specified Box folder
        Optionally, you can simply grab the download link to send to another user
        """
        oauth2 = OAuth2(self.clientId, self.clientSecret,
                        access_token=self.accessToken)
        client = Client(oauth2)
        my = client.user(user_id='me').get()
        print('connected to Box as ' + my.login)
        if box_folder is None:
            target_folder = client.folder(self.box_folder_id)
        else:
            target_folder = client.folder(box_folder)
        if use_dl_links is True:
            link_array = []
        target_folder_info = target_folder.get()
        items_in_Box_folder = target_folder.get_items(limit=None, offset=0)
        for file_name in files_to_download:
            # Check the Box folder to see if the files exist
            for item in items_in_Box_folder:
                # If the file does already exist, use update_contents
                if item.name == file_name and use_dl_links is False:
                    with open(self.temp_file_dir + file_name, 'wb') as f:
                        f.write(item.content())
                    print(file_name + ' downloaded')
                elif item.name == file_name and use_dl_links is True:
                    box_link = item.get_shared_link_download_url()
                    link_array.append(box_link)
        if use_dl_links is True:
            return link_array

    def create_Box_folder(self, box_folder, folder_array):
        oauth2 = OAuth2(self.clientId, self.clientSecret,
                        access_token=self.accessToken)
        client = Client(oauth2)
        my = client.user(user_id='me').get()
        target_folder = client.folder(box_folder)
        if isinstance(folder_array, str):
            target_folder.create_subfolder(folder_array)
        else:
            for folder in folder_array:
                target_folder.create_subfolder(folder)

    def get_items_in_Box_folder(self, box_folder=None):
        oauth2 = OAuth2(self.clientId, self.clientSecret,
                        access_token=self.accessToken)
        client = Client(oauth2)
        my = client.user(user_id='me').get()
        if box_folder is None:
            target_folder = client.folder(self.box_folder_id)
        else:
            target_folder = client.folder(box_folder)
        items_in_Box_folder = target_folder.get_items(limit=None, offset=0)
        return items_in_Box_folder


if __name__ == '__main__':
    # Sample execution
    # Not a part of the FileMover class. This can be substituted for an
    # function that would return the files to process
    def remove_trailing_zeroes(temp_file_dir, files_to_process):
        """
        Strips the last 3 characters from a file name
        """
        files = listdir(temp_file_dir)
        processed_files = []
        print('processing files')
        for filename in files:
            # Check to see if the file is one that exists in files_to_download
            if filename in set(files_to_download):
                filename_path = temp_file_dir + filename
                # Drop the 000's from the end of the filename
                new_filename = filename[:-3]
                rename(filename_path, temp_file_dir + new_filename)
                print(filename + ' -> ' + new_filename)
                processed_files.append(new_filename)
        print('processing complete')
        return processed_files
    # Name session variables
    bucket_name = 'discovery-aa/users/sberndt/'
    temp_file_dir = 'mybox-selected/'
    box_folder_id = '26209133732'
    files_to_download = ['dsc_install_android_auth.csv000',
                         'dsc_install_android_no_auth.csv000',
                         'dsc_install_ios_auth.csv000',
                         'dsc_install_ios_no_auth.csv000',
                         'id_install_android_auth.csv000',
                         'id_install_android_no_auth.csv000',
                         'id_install_ios_auth.csv000',
                         'id_install_ios_no_auth.csv000',
                         'tlc_install_android_auth.csv000',
                         'tlc_install_android_no_auth.csv000',
                         'tlc_install_ios_auth.csv000',
                         'tlc_install_ios_no_auth.csv000']

    # Download the files
    fm = FileMover(bucket_name, temp_file_dir, box_folder_id)
    for item in fm.get_items_in_Box_folder():
        print(item.id + '-' + item.name)
    csv_file = ['Harmony_Template_Deck.pdf']
    fm.download_from_box(csv_file)

    # fm.download_files_from_s3(files_to_download)
    # fm.upload_files_to_s3(files_to_download)
    # processed_files = fm.process_files(processFunction=remove_trailing_zeroes, files_to_process=files_to_download)
    # fm.upload_to_box(files_to_upload=processed_files)
