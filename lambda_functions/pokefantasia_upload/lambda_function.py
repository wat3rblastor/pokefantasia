#
# Uploads a JPEG to S3 and then inserts a new job record
# in the Pokefantasia database with the status of 'uploaded'.
# Sends the job id back to the client.
#

import json
import boto3
import os
import uuid
import base64
import pathlib
import datatier

from configparser import ConfigParser

def lambda_handler(event, context):
  try:
    print("**STARTING**")
    print("**lambda: pokefantasia_upload**")
    
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
    s3_profile = 's3readwrite'
    boto3.setup_default_session(profile_name=s3_profile)
    
    s3 = boto3.resource('s3')
    bucket_typeid = s3.Bucket('poketypeid')
    bucket_typecov = s3.Bucket('poketypecov')
    bucket_formatcov = s3.Bucket('pokeformatcov')

    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')
    
    #
    # userid from event: could be a parameter
    # or could be part of URL path ("pathParameters"):
    #
    print("**Accessing event/pathParameters for userid**")
    
    if "userid" in event:
      userid = event["userid"]
    elif "pathParameters" in event:
      if "userid" in event["pathParameters"]:
        userid = event["pathParameters"]["userid"]
      else:
        raise Exception("requires userid parameter in pathParameters")
    else:
        raise Exception("requires userid parameter in event")
        
    # 
    # action from event: could be a parameter
    # or couldbe part of URL path ("pathParameters"):
    # 
    print("**Accessing event/pathParameters for action**")

    action = ""
    
    if "action" in event:
      action = event["action"]
    elif "pathParameters" in event:
      if "action" in event["pathParameters"]:
        action = event["pathParameters"]["action"]
      else:
        raise Exception("requires action parameter in pathParameters")
    else:
      raise Exception("requires action parameter in event")
      
    if action != "typeid" and action != "typecov" and action != "formatcov":
      raise Exception("given invalid action", action)

    #
    # parse request body

    print("**Accessing request body**")

    if "body" not in event:
      raise Exception("event has no body")

    body = json.loads(event["body"])

    #
    # accessing target_type or target_format based on
    # action type
    #

    target_type = ""
    target_format = ""

    # parse json
    body = json.loads(event["body"])
    
    if action == "typecov":
      if "target_type" in event:
        target_type = event["target_type"]
      elif "body" in event:
        if "target_type" in body:
          target_type = body["target_type"]
        else:
          raise Exception("requires target_type in body")
      else:
        raise Exception("requires target_type parameter in event")
        
    if action == "formatcov":
      if "target_format" in event:
        target_format = event["target_format"]
      elif "body" in event:
        body = json.loads(event["body"])
        if "target_format" in body:
          target_format = body["target_format"]
        else:
          raise Exception("requires target_format in body")
      else:
        raise Exception("requires target_format in event")
      
  
    #
    # parse filename and data

    
    if "filename" not in body:
      raise Exception("event has a body but no filename")
    if "data" not in body:
      raise Exception("event has a body but no data")

    filename = body["filename"]
    datastr = body["data"]
    
    print("filename:", filename)
    print("datastr (first 10 chars):", datastr[0:10])

    #
    # open connection to the database:
    #
    print("**Opening connection**")
    
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

    #
    # first we need to make sure the userid is valid:
    #
    print("**Checking if userid is valid**")
    
    sql = "SELECT * FROM users WHERE userid = %s;"
    
    row = datatier.retrieve_one_row(dbConn, sql, [userid])
    
    if row == ():  # no such user
      print("**No such user, returning...**")
      return {
        'statusCode': 400,
        'body': json.dumps("no such user...")
      }
    
    print(row)
    
    username = row[1]
    
    #
    # at this point the user exists, so safe to upload to S3:
    #
    base64_bytes = datastr.encode()        # string -> base64 bytes
    bytes = base64.b64decode(base64_bytes) # base64 bytes -> raw bytes
    
    #
    # write raw bytes to local filesystem for upload:
    #
    print("**Writing local data file**")

    local_filename = "/tmp/data.jpg"
    
    outfile = open(local_filename, "wb")
    outfile.write(bytes)
    outfile.close()
    
    #
    # generate unique filename in preparation for the S3 upload:
    #
    print("**Uploading local file to S3**")
    
    basename = pathlib.Path(filename).stem
    extension = pathlib.Path(filename).suffix
    
    if extension != ".jpg" and extension != ".jpeg" : 
      raise Exception("expecting filename to have .jpg extension")
      
    bucketkey = username + "/" + basename + "-" + str(uuid.uuid4()) + ".jpg"
    
    print("S3 bucketkey:", bucketkey)

    #
    # Remember that the processing of the PNG is event-triggered,
    # and that lambda function is going to update the database as
    # is processes. So let's insert a job record into the database
    # first, THEN upload the PDF to S3. The status column should 
    # be set to 'uploaded':
    #
    print("**Adding jobs row to database**")
    
    sql = """
      INSERT INTO jobs(userid, status, originaldatafile, datafilekey, resultsfilekey, bucket)
                  VALUES(%s, %s, %s, %s, '', %s);
    """
    
    if action == "typeid":
      bucket = bucket_typeid
      bucket_name = "bucket_typeid"
    elif action == "typecov":
      bucket = bucket_typecov
      bucket_name = "bucket_typecov"
    elif action == "formatcov":
      bucket = bucket_formatcov
      bucket_name = "bucket_formatcov"

    datatier.perform_action(dbConn, sql, [userid, 'uploaded', filename, bucketkey, bucket_name])

    #
    # grab the jobid that was auto-generated by mysql:
    #
    sql = "SELECT LAST_INSERT_ID();"
    
    row = datatier.retrieve_one_row(dbConn, sql)
    
    jobid = row[0]
    
    print("jobid:", jobid)

    #
    # now that DB is updated, let's upload PNG to S3:
    #
    print("**Uploading data file to S3**")

  
    bucket.upload_file(local_filename,
                      bucketkey, 
                      ExtraArgs={
                        'ACL': 'public-read',
                        'ContentType': 'image/jpeg',
                        'Metadata': {
                          'target-type': target_type,
                          'target-format': target_format
                        }
                      })
                      

    #
    # respond in an HTTP-like way, i.e. with a status
    # code and body in JSON format:
    #
    print("**DONE, returning jobid**")
    
    return {
      'statusCode': 200,
      'body': json.dumps(str(jobid))
    }
    
  except Exception as err:
    print("**ERROR**")
    print(str(err))
    
    return {
      'statusCode': 500,
      'body': json.dumps(str(err))
    }