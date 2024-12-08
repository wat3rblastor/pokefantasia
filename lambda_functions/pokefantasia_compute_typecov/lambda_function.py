#
# Python program to open and process a JPEG file, and 
# generate an image converting a pokemon image to a given type
# 

import json
import boto3
import os
import uuid
import base64
import pathlib
import datatier
import urllib.parse
import string
import requests

from configparser import ConfigParser
from gradio_client import Client, handle_file

def lambda_handler(event, context):
  try:
    print("**STARTING**")
    print("**lambda: pokefantasia_compute_typecov**")
    
    # 
    # in case we get an exception, initial this filename
    # so we can write an error message if need be:
    #
    bucketkey_results_file = ""
    
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
    
    bucketname = configur.get('s3', 'bucket_name')
    output_bucket_name = configur.get('s3', 'output_bucket_name')
    
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketname)
    output_bucket = s3.Bucket(output_bucket_name)
    
    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')
    
    #
    # this function is event-driven by a JPEG being
    # dropped into S3. The bucket key is sent to 
    # us and obtain as follows:
    #
    bucketkey = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    print("bucketkey:", bucketkey)
      
    extension = pathlib.Path(bucketkey).suffix
    
    if extension != ".jpeg" and extension != ".jpg" : 
      raise Exception("expecting S3 document to have .jpeg extension")
    
    bucketkey_results_file = bucketkey
    
    print("bucketkey results file:", bucketkey_results_file)
      
    #
    # download JPEG from S3 to LOCAL file system:
    #
    print("**DOWNLOADING '", bucketkey, "'**")
    local_file = "/tmp/data.jpeg"
    bucket.download_file(bucketkey, local_file)


    # Get object metadata
    s3_client = boto3.client('s3')  # Create an S3 client
    response = s3_client.head_object(Bucket=bucketname, Key=bucketkey)
    
    # Access custom metadata
    metadata = response.get('Metadata', {})
    target_type = metadata.get('target-type')
  

    if target_type:
        print(f"Extracted target type from S3 metadata: {target_type}")
    else:
        raise ValueError("Target type not found in S3 metadata.")

    
    # open connection to the database
    # change status column to "processing"
    
    print("**Opening DB connection**")
    
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    sql = "UPDATE jobs SET status='processing' WHERE datafilekey=%s;"
    datatier.perform_action(dbConn, sql, [bucketkey])
    
    # 
    # Call API to convert image to different type
    client = Client("InstantX/SD35-IP-Adapter")

    type_to_prompt = {
      "normal": "Change the Pokémon into a Normal type.",
      "fire": "Change the Pokémon into a Fire type.",
      "water": "Change the Pokémon into a Water type.",
      "electric": "Change the Pokémon into an Electric type.",
      "grass": "Change the Pokémon into a Grass type.",
      "ice": "Change the Pokémon into an Ice type.",
      "fighting": "Change the Pokémon into a Fighting type.",
      "poison": "Change the Pokémon into a Poison type.",
      "ground": "Change the Pokémon into a Ground type.",
      "flying": "Change the Pokémon into a Flying type.",
      "psychic": "Change the Pokémon into a Psychic type.",
      "bug": "Change the Pokémon into a Bug type.",
      "rock": "Change the Pokémon into a Rock type.",
      "ghost": "Change the Pokémon into a Ghost type.",
      "dragon": "Change the Pokémon into a Dragon type.",
      "dark": "Change the Pokémon into a Dark type.",
      "steel": "Change the Pokémon into a Steel type.",
      "fairy": "Change the Pokémon into a Fairy type."
    }

    # Check if the type is valid
    if target_type in type_to_prompt:
        # Make the API call
        result = client.predict(
            image=handle_file(local_file),
            prompt=type_to_prompt[target_type],
            scale=0.7,
            seed=42,
            randomize_seed=True,
            width=1024,
            height=1024,
            api_name="/process_image"
        )
        print("Processing completed. File saved.")
    else:
        print(f"Error: '{target_type}' is not a valid Pokémon type.")

    # Index into dictionary
    result = result[0]
    
    print(result)
    
    # Write result into output file
    local_results_file = "/tmp/results.jpg"

    print("local results file:", local_results_file)
    
    with open(local_results_file, 'w') as outfile:
      outfile.write(result)
    
    print("Results written to local results file")
    
    #
    # upload the results file to S3:
    #
    print("**UPLOADING to S3 file", bucketkey_results_file, "**")

    output_bucket.upload_file(result,
                       bucketkey_results_file,
                       ExtraArgs={
                         'ACL': 'public-read',
                         'ContentType': 'image/jpeg'
                       })
    
    # 
    # The last step is to update the database to change
    # the status of this job, and store the results
    # bucketkey for download:
    #
    
    sql = "UPDATE jobs SET status='completed', resultsfilekey=%s WHERE datafilekey=%s;"
    datatier.perform_action(dbConn, sql, [bucketkey_results_file, bucketkey])

    #
    # done!
    #
    # respond in an HTTP-like way, i.e. with a status
    # code and body in JSON format:
    #
    print("**DONE, returning success**")
    
    return {
      'statusCode': 200,
      'body': json.dumps("success")
    }
    
  #
  # on an error, try to upload error message to S3:
  #
  except Exception as err:
    print("**ERROR**")
    print(str(err))
    
    local_results_file = "/tmp/results.txt"
    outfile = open(local_results_file, "w")

    outfile.write(str(err))
    outfile.write("\n")
    outfile.close()
    
    if bucketkey_results_file == "": 
      #
      # we can't upload the error file:
      #
      pass
    else:
      # 
      # upload the error file to S3
      #
      print("**UPLOADING**")
      #
      output_bucket.upload_file(local_results_file,
                         bucketkey_results_file,
                         ExtraArgs={
                           'ACL': 'public-read',
                           'ContentType': 'text/plain'
                         })

    #
    # update jobs row in database:
    #

    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    sql = "UPDATE jobs SET status='error', resultsfilekey=%s WHERE datafilekey=%s;"
    datatier.perform_action(dbConn, sql, [bucketkey_results_file, bucketkey])

    #
    # done, return:
    #    
    return {
      'statusCode': 500,
      'body': json.dumps(str(err))
    }
    
