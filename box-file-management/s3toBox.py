from boxsdk import Client, OAuth2
from os import listdir, rename
import re
import json
import logging
import os
import plistlib
import requests
import smtplib
import sys
from datetime import datetime
import boto
from boto.s3.key import Key
import boto.s3.connection
from configparser import ConfigParser

parser = ConfigParser()

parser.read('config.ini')

# Variables
# TODO: Create a separate file to hold configurations and passwords
# Box
oauth2URL = parser.get('Box', 'oauth2URL')
apiURL = parser.get('Box', 'apiURL')
authorizationCode = parser.get('Box', 'authorizationCode')
clientId = parser.get('Box', 'clientId')
clientSecret = parser.get('Box', 'clientSecret')
box_folder_id = '21162621210'
apiFolder = './'
logFileFullPath = os.path.join(apiFolder, os.path.basename(sys.argv[0]) + '.log')
plistFileFullPath = os.path.join(apiFolder, 'Box-API.plist')
# AWS
AWS_ACCESS_KEY_ID = parser.get('AWS', 'AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = parser.get('AWS', 'AWS_SECRET_ACCESS_KEY')
HOST = parser.get('AWS', 'HOST')
bucket_name = 'discovery-aa/users/sberndt/'
conn = boto.connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY,
        host = HOST,
        is_secure=True,
        calling_format = boto.s3.connection.OrdinaryCallingFormat(),
        )

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
temp_file_dir = 'mybox-selected/'
tempdir = os.getcwd() + "/" + temp_file_dir
# Logging
scriptName =  os.path.basename(sys.argv[0])
# Configure Logging
logging.basicConfig(filename=logFileFullPath,level=logging.DEBUG,format='%(asctime)s %(levelname)s %(message)s',filemode='w')


def downloadFilesFromS3(files_to_download_array, s3Bucket_name):
    """
    Connect to an s3 bucket in order to download the files specified
    in the varialble files_to_download
    """
    bucket = conn.get_bucket(s3Bucket_name)
    print('s3 connection successful')
    print('downloading files from s3 folder - ' + bucket_name)
    if os.path.exists(tempdir):
        pass
    else:
        os.makedirs(tempdir)
    for filename in files_to_download:
         key = boto.s3.key.Key(bucket)
         key.key = filename
         key.get_contents_to_filename(tempdir + filename)
         print(filename + " downloaded")
    print('download complete')


# Generate OAuth2 tokens
def generateTokens():
    """
    Genereates tokens to refresh authentication to Box. This must be done at
    least once every 2 months in order for the refresh token to be valid.
    """
    print('generating Box auth tokens')
    # Read this scripts plist
    try:
        # Read this scripts plist
        tokenPlist = plistlib.readPlist(plistFileFullPath)
        # Get the Refresh token from the plist
        refreshToken = tokenPlist["Refresh Token"]
    # If we can't find the plist
    except:
        # Try & generate new tokens
        try:
            # API call to generate tokens
            getTokens = requests.post(oauth2URL, data={'grant_type' : 'authorization_code','code' : authorizationCode, 'client_id' : clientId, 'client_secret' : clientSecret})
            # If the above gives a 4XX or 5XX error
            getTokens.raise_for_status()
            # Get the JSON from the above
            newTokens = getTokens.json()
            # Get the new access token, valid for 60 minutes
            accessToken = newTokens['access_token']
            # Log the access token we're using
            logging.info('Generated Access Token: %s' % accessToken)
            # Get the refresh token, valid for 60 days
            refreshToken = newTokens['refresh_token']
            # Log the new refresh token we've generated
            logging.info('Generated Refresh Token: %s' % refreshToken)
            # Update plist with new refresh token & time generated, refresh token used for subsequent runs
            plistlib.writePlist({'Refresh Token':refreshToken,'Time Generated': datetime.now().isoformat(),}, plistFileFullPath)
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
        logging.info('Using Refresh Token: %s' % refreshToken)
        # Get new access & refresh tokens
        getTokens = requests.post(oauth2URL, data={'grant_type' : 'refresh_token','refresh_token' : refreshToken, 'client_id' : clientId, 'client_secret' : clientSecret})
        # If the above gives a 4XX or 5XX error
        getTokens.raise_for_status()
        # Get the JSON from the above
        newTokens = getTokens.json()
        # Get the new access token, valid for 60 minutes
        accessToken = newTokens['access_token']
        # Log the access token we're using
        logging.info('Generated Access Token: %s' % accessToken)
        # Get the refresh token, valid for 60 days
        refreshToken = newTokens['refresh_token']
        # Log the new refresh token we've generated
        logging.info('Generated Refresh Token: %s' % refreshToken)
        # Update plist with new refresh token & time generated, refresh token used for subsequent runs
        plistlib.writePlist({'Refresh Token':refreshToken,'Time Generated': datetime.now().isoformat(),}, plistFileFullPath)
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


def getToken():
    """
    Retrieves the token that was generated in the logs by generateTokens()
    """
    print('retrieving refresh token')
    # Open the log file where the keys are kept
    with open(os.path.basename(sys.argv[0]) + '.log') as token_log:
        # Check line 4 of the log file
        token_line = token_log.readlines()[3:4]
        # Change it from an array to a string
        token_string = token_line[0]
        # Return the new token with the /n removed
        return token_string[-33:].rstrip()


def main():
    """
    Dictates what is to be done for the current process.
    Current steps:
    -Connect to s3 and download specified files to tempdir
    -Generate Refresh token and store in logs
    -Retrieve token from logs and authenticate
    -Process files by renaming them
    -Upload files to Box
    -Remove the locally stored files
    """
    downloadFilesFromS3(files_to_download_array=files_to_download, s3Bucket_name=bucket_name)
    accessToken = str(getToken())
    oauth2 = OAuth2(clientId, clientSecret, access_token=accessToken)
    client = Client(oauth2)
    my = client.user(user_id='me').get()
    print('connected to Box as ' + my.login)
    target_folder = client.folder(box_folder_id)
    # target_folder = client.folder('0')
    target_folder_info = target_folder.get()
    items_in_Box_folder = target_folder.get_items(limit=None, offset=0)

    # Grab all of the files in the temp dir
    files = listdir(temp_file_dir)
    files_to_download_set = set(files_to_download)

    # Start to upload the files to Box
    print('uploading files to folder - ' + target_folder_info.name)
    upload_array = []
    for filename in files:
        # Check to see if the file is one that exists in files_to_download
        if filename in files_to_download_set:
            filename_path = temp_file_dir + filename
            # Drop the 000's from the end of the filename
            new_filename = filename[:-3]
            rename(filename_path, temp_file_dir + new_filename)
            # Check the Box folder to see if the files exist
            for item in items_in_Box_folder:
                # If the file does already exist, use update_contents
                if item.name == new_filename:
                    box_file = item.update_contents(filename_path[:-3])
                    print(item.name + ' updated')
                    upload_array.append(new_filename)
                    break
            # If the file did not exist, use upload
            if new_filename not in set(upload_array):
                box_file = target_folder.upload(filename_path[:-3], new_filename)
                print(new_filename + ' uploaded')
            os.remove(temp_file_dir + new_filename)
    print('all files uploaded')


class FileMover(object):
    def __init__(self, s3_bucket, temp_dir, box_folder, files_to_download):
        self.oauth2URL = parser.get('Box', 'oauth2URL')
        self.apiURL = parser.get('Box', 'apiURL')
        self.authorizationCode = parser.get('Box', 'authorizationCode')
        self.clientId = parser.get('Box', 'clientId')
        self.clientSecret = parser.get('Box', 'clientSecret')
        self.box_folder_id = box_folder
        self.apiFolder = './'
        self.logFileFullPath = os.path.join(self.apiFolder, os.path.basename(sys.argv[0]) + '.log')
        self.plistFileFullPath = os.path.join(self.apiFolder, 'Box-API.plist')
        # AWS
        self.AWS_ACCESS_KEY_ID = parser.get('AWS', 'AWS_ACCESS_KEY_ID')
        self.AWS_SECRET_ACCESS_KEY = parser.get('AWS', 'AWS_SECRET_ACCESS_KEY')
        self.HOST = parser.get('AWS', 'HOST')
        self.bucket_name = s3_bucket
        self.conn = boto.connect_s3(self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY,
                                    host=HOST,
                                    is_secure=True,
                                    calling_format=boto.s3.connection.OrdinaryCallingFormat(),
                                    )
        self.files_to_download = files_to_download
        self.temp_file_dir = temp_dir
        self.tempdir = os.getcwd() + "/" + self.temp_file_dir


if __name__ == '__main__':
    generateTokens()
    main()
    print('process complete')
# TODO: Refactor code into cleaner methods
