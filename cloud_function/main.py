from google.cloud import vision
from google.cloud import storage

# setup
vision_client = vision.ImageAnnotatorClient()
image_bucket_name = 'ece528imagestorage'
json_bucket_name = 'ece528jsonstorage'

def sense_mood(event, context):
    source = {"image_uri": 'gs://' + event['bucket'] + '/' + event['name']}
    image = {"source": source}
    features = [
        {"type_": vision.Feature.Type.FACE_DETECTION},
    ]

    # Each requests element corresponds to a single image.  To annotate more
    # images, create a request element for each image and add it to
    # the array of requests
    requests = [{"image": image, "features": features}]
    gcs_destination = {"uri": 'gs://' + json_bucket_name + '/' + event['name'] + '/'}

    # The max number of responses to output in each JSON file
    batch_size = 2
    output_config = {"gcs_destination": gcs_destination,
                     "batch_size": batch_size}

    operation = vision_client.async_batch_annotate_images(requests=requests, output_config=output_config)

    print("Waiting for operation to complete...")
    response = operation.result(90)

    # The output is written to GCS with the provided output_uri as prefix
    gcs_output_uri = response.output_config.gcs_destination.uri
    print("Output written to GCS with prefix: {}".format(gcs_output_uri))

