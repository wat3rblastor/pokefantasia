#
# Resets the contents of the BenfordApp database back
# to 3 users and 0 jobs.
#

import json
import boto3
import os
import datatier

from configparser import ConfigParser

def lambda_handler(event, context):
  try:
    print("**STARTING**")
    print("**lambda: pokefantasia_reset**")
    
    #
    # setup AWS based on config file:
    #
    config_file = 'pokefantasia-config.ini'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file
    
    configur = ConfigParser()
    configur.read(config_file)
    
    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')

    #
    # open connection to the database:
    #
    print("**Opening connection**")
    
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    
    #
    # delete all rows from jobs and users:
    #
    print("**Deleting jobs**")
    
    sql = "SET FOREIGN_KEY_CHECKS = 0;"
    
    datatier.perform_action(dbConn, sql)
    
    sql = "TRUNCATE TABLE jobs";
    
    datatier.perform_action(dbConn, sql)
    
    print("**Deleting users**")
    
    sql = "TRUNCATE TABLE users";
    
    datatier.perform_action(dbConn, sql)
    
    sql = "SET FOREIGN_KEY_CHECKS = 1;"
    
    datatier.perform_action(dbConn, sql)
    
    sql = "ALTER TABLE users AUTO_INCREMENT = 80001;"
    
    datatier.perform_action(dbConn, sql)
    
    sql = "ALTER TABLE jobs AUTO_INCREMENT = 1001;"
    
    datatier.perform_action(dbConn, sql)
    
    print("**Inserting 3 users back into database...")
    
    sql = """
      INSERT INTO users(username, pwdhash)
             values('b_cheng', '$2y$10$/8B5evVyaHF.hxVx0i6dUe2JpW89EZno/VISnsiD1xSh6ZQsNMtXK');
    """
    
    datatier.perform_action(dbConn, sql)

    sql = """
      INSERT INTO users(username, pwdhash)
             values('h_wang', '$2y$10$F.FBSF4zlas/RpHAxqsuF.YbryKNr53AcKBR3CbP2KsgZyMxOI2z2');
    """
    
    datatier.perform_action(dbConn, sql)
    
    sql = """
      INSERT INTO users(username, pwdhash)
             values('s_zhu', '$2y$10$GmIzRsGKP7bd9MqH.mErmuKvZQ013kPfkKbeUAHxar5bn1vu9.sdK');
    """
    
    datatier.perform_action(dbConn, sql)

    #
    # respond in an HTTP-like way, i.e. with a status
    # code and body in JSON format:
    #
    print("**DONE, returning success**")
    
    return {
      'statusCode': 200,
      'body': json.dumps("success")
    }
    
  except Exception as err:
    print("**ERROR**")
    print(str(err))
    
    return {
      'statusCode': 500,
      'body': json.dumps(str(err))
    }