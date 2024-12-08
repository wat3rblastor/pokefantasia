#
# Python program to open and process a JPEG file, and 
# generate an image converting format of image to a given format
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
import numpy as np
import cv2
import random
import time
from configparser import ConfigParser

from math import pi
from skimage import draw


# ------------------------------a
# Style Functions
# ------------------------------

def apply_grayscale(input_image):
    """
    Converts the image to grayscale.

    Parameters:
    - input_image: The original image (numpy array).

    Returns:
    - grayscale_image: The grayscale image.
    """
    grayscale_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
    print("Grayscale conversion applied.")
    return grayscale_image

def apply_comic_effect(input_image, line_size=7, blur_value=7):
    """
    Applies a comic book style effect to an image.

    Parameters:
    - input_image: The original image (numpy array).
    - line_size: Size of edges to detect.
    - blur_value: Kernel size for median blur.

    Returns:
    - cartoon: Image with a comic book effect applied.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)

    # Apply median blur
    gray_blurred = cv2.medianBlur(gray, blur_value)

    # Detect edges using adaptive thresholding
    edges = cv2.adaptiveThreshold(
        gray_blurred,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        line_size,
        2
    )

    # Reduce the color palette
    color = cv2.bilateralFilter(input_image, d=9, sigmaColor=200, sigmaSpace=200)

    # Combine edges and reduced color palette
    cartoon = cv2.bitwise_and(color, color, mask=edges)

    print("Comic book style effect applied.")
    return cartoon

def apply_abstract_art_effect(input_image, level=6):
    """
    Converts an image into an abstract art style using posterization and color mapping.

    Parameters:
    - input_image: The original image (numpy array).
    - level: Number of intensity levels for posterization.

    Returns:
    - colorized: The abstract art-styled image.
    """
    def posterize(image, level):
        indices = np.arange(0, 256)
        divider = np.linspace(0, 255, level + 1)[1]
        quantiz = np.int32(np.linspace(0, 255, level))  # Corrected from np.int0 to np.int32
        color_levels = np.clip(np.int32(indices / divider), 0, level - 1)  # Corrected from np.int0 to np.int32
        palette = quantiz[color_levels]
        img2 = palette[image]
        img2 = cv2.convertScaleAbs(img2)
        return img2

    # Grayscale conversion
    grayed = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
    # Gaussian blur
    blurred = cv2.GaussianBlur(grayed, (51, 51), 0)
    # Posterization
    poster = posterize(blurred, level)
    # Color mapping
    colorized = cv2.applyColorMap(poster, cv2.COLORMAP_RAINBOW)

    print("Abstract art effect applied using posterization and color mapping.")
    return colorized

def apply_stylization(input_image, sigma_s=60, sigma_r=0.6):
    """
    Applies a stylization effect to the image using OpenCV's stylization.

    Parameters:
    - input_image: The original image (numpy array).
    - sigma_s: Filter sigma in the spatial domain.
    - sigma_r: Filter sigma in the intensity domain.

    Returns:
    - stylized_image: The stylized image.
    """
    stylized_image = cv2.stylization(input_image, sigma_s=sigma_s, sigma_r=sigma_r)
    print("Stylization effect applied.")
    return stylized_image

def apply_sketch(input_image):
    """
    Applies a grayscale pencil sketch effect to the image using OpenCV's pencilSketch.

    Parameters:
    - input_image: The original image (numpy array).

    Returns:
    - sketch_image: The grayscale pencil sketch image.
    """
    dst_gray, _ = cv2.pencilSketch(input_image, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
    print("Grayscale pencil sketch applied successfully.")
    return dst_gray

def apply_color_pencil_sketch(input_image):
    """
    Applies a color pencil sketch effect to the image using OpenCV's pencilSketch.

    Parameters:
    - input_image: The original image (numpy array).

    Returns:
    - color_sketch_image: The color pencil sketch image.
    """
    _, dst_color = cv2.pencilSketch(input_image, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
    print("Color pencil sketch applied successfully.")
    return dst_color



def lambda_handler(event, context):
  try:
    print(event)
    print("**STARTING**")
    print("**lambda: pokefantasia_compute_formatcov**")
    
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
    data = "/tmp/data.jpeg"
    bucket.download_file(bucketkey, data)
    input_image = cv2.imread(data)



    # Get object metadata
    s3_client = boto3.client('s3')  # Create an S3 client
    response = s3_client.head_object(Bucket=bucketname, Key=bucketkey)
    
    # Access custom metadata
    metadata = response.get('Metadata', {})
    target_format = metadata.get('target-format')
  
    if target_format:
        print(f"Extracted target type from S3 metadata: {target_format}")
    else:
        raise ValueError("Target format not found in S3 metadata.")

    
    # open connection to the database
    # change status column to "processing"
    
    print("**Opening DB connection**")
    
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    sql = "UPDATE jobs SET status='processing' WHERE datafilekey=%s;"
    datatier.perform_action(dbConn, sql, [bucketkey])
    
    #
    # apply selected style

    if target_format == 'grayscale':
        transformed_image = apply_grayscale(input_image)
    elif target_format == 'comic':
        line_size = 7
        blur_value = 7
        transformed_image = apply_comic_effect(input_image, line_size, blur_value)
    elif target_format == 'abstract':
        level = 6
        transformed_image = apply_abstract_art_effect(input_image, level)
    elif target_format == 'stylization':
        sigma_s = 60
        sigma_r = 0.6
        transformed_image = apply_stylization(input_image, sigma_s, sigma_r)
    elif target_format == 'sketch':
        transformed_image = apply_sketch(input_image)
    elif target_format == 'color_pencil_sketch':
        transformed_image = apply_color_pencil_sketch(input_image)
    else:
        print(f"Error: Style '{target_format}' is not supported.")
        raise Exception(f"Error: Style '{target_format}' is not supported.")

    
    # Write result into output file
    local_results_file = "/tmp/results.jpg"

    print("local results file:", local_results_file)
    
    cv2.imwrite(local_results_file, transformed_image)
    
    print("Results written to local results file")
    
    #
    # upload the results file to S3:
    #
    print("**UPLOADING to S3 file", bucketkey_results_file, "**")

    output_bucket.upload_file(local_results_file,
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
  