#
# Downloads the requested job from the Pokefantasia DB, checks
# the status, and based on the status returns results
# to the client. The status can be: uploaded, processing,
# completed, or error. In the case of completed, the 
# analysis results are returned as a list. In the case
# of error, the error message from the results file is
# returned.
#

import json
import boto3
import os
import base64
import datatier

from configparser import ConfigParser

def lambda_handler(event, context):
  try:
    print("**STARTING**")
    print("**lambda: pokefantasia_download**")

    #
    # setup AWS based on config file:
    #
    config_file = 'pokefantasia-config.ini'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file
    
    configur = ConfigParser()
    configur.read(config_file)
    
    #
    # configure for S3 access:
    #
    s3_profile = 's3readonly'
    boto3.setup_default_session(profile_name=s3_profile)
    
    s3 = boto3.resource('s3')
    
    bucket_typeid = s3.Bucket("poketypeid-output")
    bucket_typecov = s3.Bucket("poketypecov-output")
    bucket_formatcov = s3.Bucket("pokeformatcov-output")
    
    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')
    
    #
    # jobid from event: could be a parameter
    # or could be part of URL path ("pathParameters"):
    #
    if "jobid" in event:
      jobid = event["jobid"]
    elif "pathParameters" in event:
      if "jobid" in event["pathParameters"]:
        jobid = event["pathParameters"]["jobid"]
      else:
        raise Exception("requires jobid parameter in pathParameters")
    else:
        raise Exception("requires jobid parameter in event")
        
    print("jobid:", jobid)

    #
    # does the jobid exist?  What's the status of the job if so?
    #
    # open connection to the database:
    #
    print("**Opening connection**")
    
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

    #
    # first we need to make sure the userid is valid:
    #
    print("**Checking if jobid is valid**")
    
    sql = "SELECT * FROM jobs WHERE jobid = %s;"
    
    row = datatier.retrieve_one_row(dbConn, sql, [jobid])
    
    if row == ():  # no such job
      print("**No such job, returning...**")
      return {
        'statusCode': 400,
        'body': json.dumps({
          'text': 'no such job...'
        })
      }
    
    print(row)
    
    status = row[2]
    original_data_file = row[3]
    results_file_key = row[5]
    bucket_name = row[6]
    
    if bucket_name == "bucket_typeid":
      bucket = bucket_typeid
    elif bucket_name == "bucket_typecov":
      bucket = bucket_typecov
    elif bucket_name == "bucket_formatcov":
      bucket = bucket_formatcov
    else:
      raise Exception("Error with bucket_name in database")
    
    
    print("job status:", status)
    print("original data file:", original_data_file)
    print("results file key:", results_file_key)
    
    #
    # what's the status of the job? There should be 4 cases:
    #   uploaded
    #   processing - ...
    #   completed
    #   error
    #
    if status == "uploaded":
      print("**No results yet, returning...**")
      #
      return {
        'statusCode': 480,
        'body': json.dumps({
          'text': status
        })
      }

    if status == "processing":
      print("**No results yet, returning...**")
      #
      return {
        'statusCode': 481,
        'body': json.dumps({
          'text': status
        })
      }

    #
    # completed or error, these should have results:
    #

    if status == 'error':
      #
      # let's download the results if available, and return the
      # error message in the results file:
      #
      if results_file_key == "":
        print("**Job status 'unknown error', returning...**")
        #
        return {
          'statusCode': 482,
          'body': json.dumps({
            'text': 'error: unknown'
          })
        }
      
      local_filename = "/tmp/results.txt"
      #
      print("**Job status 'error', downloading error results from S3**")
      #
      bucket.download_file(results_file_key, local_filename)
      #
      infile = open(local_filename, "r")
      lines = infile.readlines()
      infile.close()
      #
      if len(lines) == 0:
        print("**Job status 'unknown error', given empty results file, returning...**")
        #
        return {
          'statusCode': 482,
          'text': json.dumps("error: unknown, results file was empty")
        }
        
      msg = "error: " + lines[0]
      #
      print("**Job status 'error', results msg:", msg)
      print("**Returning error msg to client...")
      #
      return {
        'statusCode': 482,
        'body': json.dumps({
          'text': msg
        })
      }
    
    #
    # at this point, either completed or something unexpected:
    #
    if status != "completed":
      print("**Job status is an unexpected value:", status)
      print("**Returning to client...**")
      #
      msg = "error: unexpected job status of '" + status + "'"
      #
      return {
        'statusCode': 482,
        'body': json.dumps({
          'text': msg
        })
      }
      
    #
    # if we get here, the job completed. So we should have results
    # to download and return to the user:
    #      
    local_filename = "/tmp/results.txt"
    
    print("**Downloading results from S3**")
    
    bucket.download_file(results_file_key, local_filename)
    
  
    #
    # open the file and read as raw bytes:
    #
    infile = open(local_filename, "rb")
    bytes = infile.read()
    infile.close()
    
    #
    # now encode the data as base64. Note b64encode returns
    # a bytes object, not a string. So then we have to convert
    # (decode) the bytes -> string, and then we can serialize
    # the string as JSON for download:
    #
    data = base64.b64encode(bytes)
    datastr = data.decode()

    print("**DONE, returning results**")
    
    #
    # respond in an HTTP-like way, i.e. with a status
    # code and body in JSON format:
    #
    
    if bucket_name == "bucket_typeid":
      return {
        'statusCode': 200,
        'body': json.dumps({
          'text': datastr
        })
      }
    else:
      return {
        'statusCode': 200,
        'body': json.dumps({
          'image': datastr
        })
      }
    

  #
  # we end up here if an exception occurs:
  #
  except Exception as err:
    print("**ERROR**")
    print(str(err))
    
    return {
      'statusCode': 500,
      'body': json.dumps(str(err))
    }
