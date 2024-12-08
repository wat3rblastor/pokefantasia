import json
import boto3
import os
import uuid
import base64
import pathlib
import datatier
import urllib.parse
import string
from PIL import Image
import numpy as np
import io
import onnxruntime as ort
from configparser import ConfigParser


def preprocess_image(image_path, image_mean, image_std):
    # Load image
    image = Image.open(image_path).convert("RGB")

    # Resize to match model input
    image = image.resize((224, 224))
    
    # Normalize
    img_array = np.array(image).astype("float32") / 255.0

    for i in range(3):
        img_array[..., i] = (img_array[..., i] - image_mean[i]) / image_std[i]
    
    # Transpose to [C, H, W]
    img_array = np.transpose(img_array, (2, 0, 1))
    
    # Add batch dimension [1, C, H, W]
    img_array = np.expand_dims(img_array, 0)
    return img_array

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    try:
        print(event)
        print("**STARTING**")
        print("**lambda: pokefantasia_compute_typeid**")
        
        
        # Pre-defined label mappings
        labels_dict = {
            'Grass': 0, 'Fire': 1, 'Water': 2, 'Bug': 3, 'Normal': 4, 'Poison': 5, 'Electric': 6,
            'Ground': 7, 'Fairy': 8, 'Fighting': 9, 'Psychic': 10, 'Rock': 11, 'Ghost': 12,
            'Ice': 13, 'Dragon': 14, 'Dark': 15, 'Steel': 16, 'Flying': 17
        }
        idx_to_label = {v: k for k, v in labels_dict.items()}
        
        image_mean = [0.5, 0.5, 0.5]  
        image_std = [0.5, 0.5, 0.5]
        
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
        model_bucket = s3.Bucket("pokefantasia")
        
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
        
        if extension == ".jpeg":
            bucketkey_results_file = bucketkey[:-5] + ".txt"
        elif extension == ".jpg":
            bucketkey_results_file = bucketkey[:-4] + ".txt"
        
        print("bucketkey results file:", bucketkey_results_file)
          
        #
        # download JPEG from S3 to LOCAL file system:
        #
        print("**DOWNLOADING '", bucketkey, "'**")
        local_file = "/tmp/data.jpeg"
        image_path = local_file
        bucket.download_file(bucketkey, local_file)
        
        # 
        # download ML model from S3
        #
        local_model = "/tmp/model.onnx"
        model_path = local_model
        model_bucket.download_file("pokemon_model/vit_pokemon_model.onnx", local_model)
        
        print("**Opening DB connection**")
    
        dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
        sql = "UPDATE jobs SET status='processing' WHERE datafilekey=%s;"
        datatier.perform_action(dbConn, sql, [bucketkey])
            
        # Preprocess the image
        input_tensor = preprocess_image(image_path, image_mean, image_std)
        
        # Initialize the ONNX runtime session
        session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        input_name = session.get_inputs()[0].name

        # Run inference
        outputs = session.run(None, {input_name: input_tensor})
        logits = outputs[0]
    
        # Get predicted class
        predicted_class_idx = np.argmax(logits, axis=1)[0]
        predicted_class = idx_to_label[predicted_class_idx]

        # Update job status to "completed" and store result in the database
        print("Updating database status to 'completed'")
        result = {
            'predicted_type': predicted_class,
        }

        sql = "UPDATE jobs SET status='completed', resultsfilekey=%s WHERE datafilekey=%s;"
        datatier.perform_action(dbConn, sql, [bucketkey_results_file, bucketkey])

        # Save results back to S3
        print("Uploading results to S3")

        # Save result to a temporary JSON file
        temp_result_file = "/tmp/result.json"
        with open(temp_result_file, "w") as f:
            json.dump(result, f)

        # Upload the temporary JSON file to S3
        output_bucket.upload_file(
            temp_result_file,
            bucketkey_results_file,
            ExtraArgs={
                'ACL': 'public-read',
                'ContentType': 'application/json'
            }
)

        print("**DONE**")
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }

    except Exception as e:
        print("**ERROR**")
        print(str(e))

        # Update job status to "error" in the database
        dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
        sql = "UPDATE jobs SET status='error', resultsfilekey=%s WHERE datafilekey=%s;"
        datatier.perform_action(dbConn, sql, [bucketkey_results_file, bucketkey])

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }